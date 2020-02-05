# FSx-PoC-Environment

## 関連ドキュメント

- [よくある質問](https://aws.amazon.com/jp/fsx/windows/faqs/?nc=sn&loc=7)
- [ユーザーガイド](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/what-is.html)
- [CLI](https://docs.aws.amazon.com/cli/latest/reference/fsx/index.html)
- [API](https://docs.aws.amazon.com/fsx/latest/APIReference/welcome.html)
- [Getting Started with Amazon FSx](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/getting-started.html)
- [AWS Managed Microsoft AD のグループポリシーを使用して、ドメインユーザーに EC2 Windows インスタンスへの RDP アクセスを許可する方法を教えてください。](https://aws.amazon.com/jp/premiumsupport/knowledge-center/ec2-domain-user-rdp/)
- [AWS Managed Microsoft AD のユーザーとグループを管理する](https://docs.aws.amazon.com/ja_jp/directoryservice/latest/admin-guide/ms_ad_manage_users_groups.html)

## 前提

- デプロイは管理者権限を持つIAMユーザーの権限で行うため、IAMユーザーを用意して下さい。
- あらかじめ、環境をデプロイするリージョンにキーペアを用意して下さい。このキーペアをEC2インスタンスに設定します。
- 以下のソフウェアがインストール済みであることを確認して下さい。

```
aws --version
python3 --version
node --version
npm --version
git --version
jq --version
```

## CDKでのベースインフラストラクチャのデプロイ

### CDKのインストール

CDKをグローバルにインストールします。

```
npm install -g aws-cdk
```

### CDKプロジェクトのクローン

CDKプロジェクトをローカルにクローンします。

```
git clone https://github.com/sotoiwa/FSx-PoC-Environment.git
cd FSx-PoC-Environment
```

### Pythonの準備

Pythonのvirtualenvを作成して有効化します。

```
python3 -m venv .env
source .env/bin/activate
```

必要なpipモジュールをインストールします。

```
pip install -r requirements.txt
```

### 環境に合わせたカスタマイズ

`cdk.context.sample.json`を`cdk.context.json`としてコピーし、パラメータをいい感じに設定して下さい。

```
cp cdk.context.sample.json cdk.context.json
```

### デプロイ

CDKが使用するバケットを作成します。

```
cdk bootstrap
```

VPC、踏み台Windowsホスト、MicrosoftADをデプロイします。

```
cdk deploy *Stack --require-approval never
```

## 踏み台WindowsをADに参加

- [Windows インスタンスを手動で参加させる](https://docs.aws.amazon.com/ja_jp/directoryservice/latest/admin-guide/join_windows_instance.html)

ADのDNSアドレスを確認します。

```
aws ds describe-directories | jq -r '.DirectoryDescriptions[] | select( .Name == "corp.example.com" ) | .DnsIpAddrs[]'
```

RDPで踏み台Windowsに接続し、PowerShellを起動します。あるいは、セッションマネージャーでPowerShellを起動します。

AD管理に必要なツールをPowerShellでインストールします。

```
Import-Module ServerManager
Get-WindowsFeature
Install-WindowsFeature -Name GPMC,RSAT-AD-Tools,RSAT-DNS-Server
Get-WindowsFeature
```

DNSを変更します。

```
Get-NetAdapter | Get-DnsClientServerAddress
Get-NetAdapter | Set-DnsClientServerAddress -ServerAddresses <1つ目のIPアドレス>,<2つ目のIPアドレス>
Get-NetAdapter | Get-DnsClientServerAddress
```

ADに参加します。Adminのパスワードを聞かれるので、`cdk.context.json`に記載したパスワードを入力します。
セッションマネージャーではなくRDPで実行して下さい。

```
$user = 'corp.example.com\Admin'
$password = ConvertTo-SecureString -AsPlainText '<パスワード>' -Force
$Credential = New-Object System.Management.Automation.PsCredential($user, $password)
Add-Computer -DomainName corp.example.com -Credential $Credential
```

変更を反映するためリブートします。

```
Restart-Computer -Force
```

## DFS

- [Scaling Out Storage and Throughput with DFS Namespaces](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/group-file-systems.html)

上記リンク先のCFnテンプレートをローカルにダウンロードします。

```
curl -o https://s3.amazonaws.com/solution-references/fsx/dfs/setup-DFSN-servers.template
```

Lambdaのランタイム指定が古いので変更します。

```
cat setup-DFSN-servers.template | sed -e s/nodejs8.10/nodejs12.x/g > setup-DFSN-servers.yaml
```

パラメータファイルを作成します。

```
DirectoryId=$(aws ds describe-directories | jq -r '.DirectoryDescriptions[] | select( .Name == "corp.example.com" ) | .DirectoryId')
KeyName=$(cat cdk.context.json | jq -r '.key_name')
SecurityGroup=$(aws ec2 describe-security-groups | jq -r '.SecurityGroups[] | select ( .GroupName | test("InternalSecurityGroup") ) | .GroupId')
Subnets=( $(aws ec2 describe-subnets | jq -r '.Subnets[] | select( .Tags ) | select( [ select( .Tags[].Value | test("Isolated") ) ] | length > 0 ) | .SubnetId') )
cat <<EOF >setup-DFSN-servers.parameter.json
{
  "Parameters": [
    {
      "ParameterKey": "DirectoryId",
      "ParameterValue": "${DirectoryId}"
    },
    {
      "ParameterKey": "KeyName",
      "ParameterValue": "${KeyName}"
    },
    {
      "ParameterKey": "InstanceType",
      "ParameterValue": "t3.large"
    },
    {
      "ParameterKey": "SecurityGroup",
      "ParameterValue": "${SecurityGroup}"
    },
    {
      "ParameterKey": "Subnet",
      "ParameterValue": "${Subnets[0]},${Subnets[1]}"
    },
    {
      "ParameterKey": "WindowsVersion",
      "ParameterValue": "Windows Server 2016 English 64-bit"
    }
  ]
}
EOF
```

スタックをデプロイします。

```
aws cloudformation create-stack \
  --stack-name FSx-DFSStack \
  --template-body file://setup-DFSN-servers.yaml \
  --cli-input-json file://setup-DFSN-servers.parameter.json \
  --capabilities CAPABILITY_IAM
```
