# FSx-PoC-Environment

#### インフラ構成

![](architecture1.png)

#### Active Directory構成

![](architecture2.png)

## 関連ドキュメント

- [よくある質問](https://aws.amazon.com/jp/fsx/windows/faqs/?nc=sn&loc=7)
- [ユーザーガイド](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/what-is.html)
- [FSx CLI](https://docs.aws.amazon.com/cli/latest/reference/fsx/index.html)
- [FSx API](https://docs.aws.amazon.com/fsx/latest/APIReference/welcome.html)
- [Getting Started with Amazon FSx](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/getting-started.html)
- [AWS Managed Microsoft AD のグループポリシーを使用して、ドメインユーザーに EC2 Windows インスタンスへの RDP アクセスを許可する方法を教えてください。](https://aws.amazon.com/jp/premiumsupport/knowledge-center/ec2-domain-user-rdp/)
- [AWS Managed Microsoft AD のユーザーとグループを管理する](https://docs.aws.amazon.com/ja_jp/directoryservice/latest/admin-guide/ms_ad_manage_users_groups.html)
- [Windows インスタンスを手動で参加させる](https://docs.aws.amazon.com/ja_jp/directoryservice/latest/admin-guide/join_windows_instance.html)

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

FSx以外のリソースをデプロイします。

```
cdk deploy *NetworkStack *BastionStack *LocalDomainStack *ManagedADStack --require-approval never
```

## domain.local

### ドメインコントローラーの作成

`domain.local`のドメインを作成します。

踏み台サーバーを経由してドメインコントローラー用のWindowsにRDPし、PowerShellを起動します。あるいは、セッションマネージャーでPowerShellを起動します。

ADドメインサービスの機能をインストールします。

```
Import-Module ServerManager
Get-WindowsFeature
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools
Get-WindowsFeature
```

ドメインコントローラーに昇格させます。

```
#
# AD DS 配置用の Windows PowerShell スクリプト
#

Import-Module ADDSDeployment
Install-ADDSForest `
-CreateDnsDelegation:$false `
-DatabasePath "C:\Windows\NTDS" `
-DomainMode "Win2012R2" `
-DomainName "domain.local" `
-DomainNetbiosName "DOMAIN" `
-ForestMode "Win2012R2" `
-InstallDns:$true `
-LogPath "C:\Windows\NTDS" `
-NoRebootOnCompletion:$false `
-SysvolPath "C:\Windows\SYSVOL" `
-Force:$true
```

### クライアントWindowsのドメインへの参加

ドメインコントローラーのIPアドレスを確認します。

```
aws ec2 describe-instances | \
  jq -r '.Reservations[].Instances[] |
           select( .Tags ) | 
           select( [ select( .Tags[].Value | test("DomainControllerWindows") ) ] | length > 0 ) | 
           .PrivateIpAddress'
```

踏み台サーバーを経由してクライアント用のWindowsにRDPし、PowerShellを起動します。あるいは、セッションマネージャーでPowerShellを起動します。

DNSを変更します。

```
Get-NetAdapter | Get-DnsClientServerAddress
Get-NetAdapter | Set-DnsClientServerAddress -ServerAddresses <ドメインコントローラのIPアドレス>
Get-NetAdapter | Get-DnsClientServerAddress
```

ADに参加します。ここで入力するパスワードはマネージメントコンソールでLocalDomainControllerWindowsインスタンスの「接続」から確認します。

```
$user = 'domain.local\Administrator'
$password = ConvertTo-SecureString -AsPlainText '<パスワード>' -Force
$Credential = New-Object System.Management.Automation.PsCredential($user, $password)
Add-Computer -DomainName domain.local -Credential $Credential
```

変更を反映するためリブートします。

```
Restart-Computer -Force
```

## corp.example.com

### クライアントWindowsのドメインへの参加

ADのDNSサーバーのアドレスを確認します。

```
aws ds describe-directories | \
  jq -r '.DirectoryDescriptions[] | select( .Name == "corp.example.com" ) | .DnsIpAddrs[]'
```

踏み台サーバーを経由してクライアント用のWindowsにRDPし、PowerShellを起動します。あるいは、セッションマネージャーでPowerShellを起動します。

AD管理に必要なツールをPowerShellでインストールします。

```
Import-Module ServerManager
Get-WindowsFeature
Install-WindowsFeature -Name GPMC,RSAT-AD-Tools,RSAT-DNS-Server
Get-WindowsFeature
```

DNSサーバーを変更します。

```
Get-NetAdapter | Get-DnsClientServerAddress
Get-NetAdapter | Set-DnsClientServerAddress -ServerAddresses <1つ目のIPアドレス>,<2つ目のIPアドレス>
Get-NetAdapter | Get-DnsClientServerAddress
```

ADに参加します。`cdk.context.json`に記載したManaged ADのパスワードを入力します。

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

## FSxのデプロイ

`cdk.context.json`にdomain.localのドメインコントローラーのIPアドレスと、Administratorのパスワードを記載します。

FSxリソースをデプロイします。

```
cdk deploy *FSxStack --require-approval never
```

## ドメインユーザーのRDPの許可



## domain.localのマウント確認

DNS名をを確認します。

```
aws fsx describe-file-systems | \
  jq -r '.FileSystems[] |
           select( .Tags ) | 
           select( [ select( .Tags[].Value | test("LocalDomainFileSystem") ) ] | length > 0 ) | 
           .DNSName'
```

RDPでネットワークドライブを割り当てます。

## Active Directoryでのユーザー追加

ユーザーを作成します。

```
Get-ADUser -Filter *
$user = 'test'
$password = ConvertTo-SecureString -AsPlainText 'Password99!' -Force
New-ADUser $user -AccountPassword $password
```

グループに追加します。

```
Get-ADGroup -Filter *
Add-ADGroupMember -Identity Administrators -Members test
Get-ADGroupMember -Identity Administrators
```