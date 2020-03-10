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

## 前提

- デプロイは管理者権限を持つIAMユーザーの権限で行うため、IAMユーザーを用意して下さい。
- あらかじめ、環境をデプロイするリージョンにキーペアを用意して下さい。このキーペアをEC2インスタンスに設定します。
- 以下のソフウェアがインストール済みであることを確認して下さい。
    ```shell
    aws --version
    python3 --version
    node --version
    npm --version
    git --version
    jq --version
    ```
- 上記環境を整えるのが面倒な場合はCloud9の利用がお奨めです。以下の手順を参考にCloud9をセットアップしてください。
  - [Cloud9環境のセットアップ](https://github.com/sotoiwa/Analytics-PoC-Environment/blob/master/cloud9.md)

## CDKでのベースインフラストラクチャのデプロイ

### CDKのインストール

CDKをグローバルにインストールします。

```shell
npm install -g aws-cdk
```

### CDKプロジェクトのクローン

CDKプロジェクトをローカルにクローンします。

```shell
git clone https://github.com/sotoiwa/FSx-PoC-Environment.git
cd FSx-PoC-Environment
```

### Pythonの準備

Pythonのvirtualenvを作成して有効化します。

```shell
python3 -m venv .env
source .env/bin/activate
```

必要なpipモジュールをインストールします。

```shell
pip install -r requirements.txt
```

### 環境に合わせたカスタマイズ

`cdk.sample.json`を`cdk.json`としてコピーし、パラメータをいい感じに設定して下さい。

```shell
cp cdk.sample.json cdk.json
```

### デプロイ

CDKが使用するバケットを作成します。

```shell
cdk bootstrap
```

VPCと踏み台インスタンスをデプロイします。

```shell
cdk deploy *NetworkStack *BastionStack --require-approval never
```

## resource.example.com（Self-managed AD）のセットアップ

ドメインコントローラー用のWindowsインスタンスと、このドメインの管理下に置くメンバー用のWindowsインスタンスをデプロイします。

```shell
cdk deploy *ResourceDomainStack --require-approval never
```

### ドメインコントローラーの作成

`resource.example.com`のドメインを作成します。

踏み台インスタンス（BastionStack/Bastion）を経由してドメインコントローラーインスタンス（ResourceDomainStack/DomainController）にRDPし、PowerShellを起動します。
あるいは、セッションマネージャーでPowerShellを起動します。

ADドメインサービスの機能をインストールします。

```powershell
Import-Module ServerManager
Get-WindowsFeature
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools
Get-WindowsFeature
```

ドメインコントローラーに昇格させます。セーフモード用のパスワードを聞かれるので入力します。

（ドメインの機能レベル2012R2の場合）

```powershell
#
# AD DS 配置用の Windows PowerShell スクリプト
#

Import-Module ADDSDeployment
Install-ADDSForest `
-CreateDnsDelegation:$false `
-DatabasePath "C:\Windows\NTDS" `
-DomainMode "Win2012R2" `
-DomainName "resource.example.com" `
-DomainNetbiosName "RESOURCE" `
-ForestMode "Win2012R2" `
-InstallDns:$true `
-LogPath "C:\Windows\NTDS" `
-NoRebootOnCompletion:$false `
-SysvolPath "C:\Windows\SYSVOL" `
-Force:$true
```

（ドメインの機能レベル2016の場合）

```
#
# AD DS 配置用の Windows PowerShell スクリプト
#

Import-Module ADDSDeployment
Install-ADDSForest `
-CreateDnsDelegation:$false `
-DatabasePath "C:\Windows\NTDS" `
-DomainMode "WinThreshold" `
-DomainName "resource.example.com" `
-DomainNetbiosName "RESOURCE" `
-ForestMode "WinThreshold" `
-InstallDns:$true `
-LogPath "C:\Windows\NTDS" `
-NoRebootOnCompletion:$false `
-SysvolPath "C:\Windows\SYSVOL" `
-Force:$true
```

自動的に再起動するのでしばらく待ちます。

### メンバーのドメインへの参加

ドメインコントローラーのIPアドレスを確認します。

```shell
aws ec2 describe-instances | \
  jq -r '.Reservations[].Instances[] |
           select( .Tags ) | 
           select( [ select( .Tags[].Value | test("ResourceDomain") and test("DomainController") ) ] | length > 0 ) | 
           .PrivateIpAddress'
```

踏み台インスタンスを経由してメンバーインスタンス（ResourceDomainStack/Member）にRDPし、PowerShellを起動します。
あるいは、セッションマネージャーでPowerShellを起動します。

DNSサーバーを変更します。

```powershell
Get-NetAdapter | Get-DnsClientServerAddress
Get-NetAdapter | Set-DnsClientServerAddress -ServerAddresses <ドメインコントローラのIPアドレス>
Get-NetAdapter | Get-DnsClientServerAddress
```

ADに参加します。ここで入力するパスワードはマネジメントコンソールでドメインコントローラーインスタンスの「接続」から確認します。

```powershell
$user = 'resource.example.com\Administrator'
$password = ConvertTo-SecureString -AsPlainText '<パスワード>' -Force
$Credential = New-Object System.Management.Automation.PsCredential($user, $password)
Add-Computer -DomainName resource.example.com -Credential $Credential
```

変更を反映するためリブートします。

```powershell
Restart-Computer -Force
```

### メンバーインスタンスへのログイン確認

踏み台インスタンスから、メンバーインスタンスに`Administrator@resource.example.com`でRDPできることを確認します。
このユーザーのパスワードはドメインコントローラーの`Administrator`ユーザーのパスワードなので、マネジメントコンソールで確認できます。

## japan.example.com（Self-managed AD）のセットアップ

ドメインコントローラー用のWindowsインスタンスをデプロイします。

```shell
cdk deploy *JapanDomainStack --require-approval never
```

### ドメインコントローラーの作成

`japan.example.com`のドメインを作成します。

踏み台インスタンスを経由してドメインコントローラーインスタンス（JapanDomainStack/DomainController）にRDPし、PowerShellを起動します。
あるいは、セッションマネージャーでPowerShellを起動します。

ADドメインサービスの機能をインストールします。

```powershell
Import-Module ServerManager
Get-WindowsFeature
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools
Get-WindowsFeature
```

ドメインコントローラーに昇格させます。セーフモード用のパスワードを聞かれるので入力します。

（ドメインの機能レベル2012R2の場合）

```powershell
#
# AD DS 配置用の Windows PowerShell スクリプト
#

Import-Module ADDSDeployment
Install-ADDSForest `
-CreateDnsDelegation:$false `
-DatabasePath "C:\Windows\NTDS" `
-DomainMode "Win2012R2" `
-DomainName "japan.example.com" `
-DomainNetbiosName "JAPAN" `
-ForestMode "Win2012R2" `
-InstallDns:$true `
-LogPath "C:\Windows\NTDS" `
-NoRebootOnCompletion:$false `
-SysvolPath "C:\Windows\SYSVOL" `
-Force:$true
```

（ドメインの機能レベル2016の場合）

```
#
# AD DS 配置用の Windows PowerShell スクリプト
#

Import-Module ADDSDeployment
Install-ADDSForest `
-CreateDnsDelegation:$false `
-DatabasePath "C:\Windows\NTDS" `
-DomainMode "WinThreshold" `
-DomainName "japan.example.com" `
-DomainNetbiosName "JAPAN" `
-ForestMode "WinThreshold" `
-InstallDns:$true `
-LogPath "C:\Windows\NTDS" `
-NoRebootOnCompletion:$false `
-SysvolPath "C:\Windows\SYSVOL" `
-Force:$true
```

自動的に再起動するのでしばらく待ちます。

### ユーザーの作成

踏み台インスタンスを経由してドメインコントローラーインスタンスにRDPし、PowerShellを起動します。
あるいは、セッションマネージャーでPowerShellを起動します。

ユーザーを作成します。

```powershell
Get-ADUser -Filter *
$user = 'user1'
$password = ConvertTo-SecureString -AsPlainText '<パスワード>' -Force
New-ADUser $user -AccountPassword $password -Enabled $true -PasswordNeverExpires $true
Get-ADUser -Filter *
```

Administratorsグループに追加します。

```powershell
Get-ADGroup -Filter *
Add-ADGroupMember -Identity Administrators -Members $user
Get-ADGroupMember -Identity Administrators
Get-ADGroup -Filter *
```

### ドメインコントローラーへのログイン確認

踏み台インスタンスから、ドメインコントローラーに`user1@japan.example.com`でRDPできることを確認します。

## 信頼関係の作成

RESOURCEドメインとJAPANドメインで双方向の信頼関係を結びます。

- [Tutorial: Create a Trust Relationship Between Your AWS Managed Microsoft AD and Your On-Premises Domain](https://docs.aws.amazon.com/directoryservice/latest/admin-guide/ms_ad_tutorial_setup_trust.html)
- [オンプレの AD DS と AWS の Microsoft AD 間で片方向信頼関係を結ぶ](https://www.vwnet.jp/Windows/Other/2017020601/AWS_MSAD_trust.htm)

### 条件付きフォワーダーの作成

#### RESOURCEドメイン

resource.example.comのドメインコントローラーで以下の作業を実施します。

```powershell
Get-DnsServerZone
Add-DnsServerConditionalForwarderZone `
    -Name "japan.example.com" `
    -MasterServers <JAPANのドメインコントローラーのアドレス> `
    -ReplicationScope "Forest"
Get-DnsServerZone
```

#### JAPANドメイン

japan.example.comのドメインコントローラーで以下の作業を実施します。

```powershell
Get-DnsServerZone
Add-DnsServerConditionalForwarderZone `
    -Name "resource.example.com" `
    -MasterServers <RESOURCEのドメインコントローラーのアドレス> `
    -ReplicationScope "Forest"
Get-DnsServerZone
```

### 信頼関係の作成 

この作業をPowerShellでやるのは難しいのでここはGUIを使います。

#### RESOURCEドメイン

resource.example.comのドメインコントローラーで以下の作業を実施します。

1. サーバーマネージャーの右上のツールから「Active Directory ドメインと信頼関係」を開きます。
1. 左のペインでドメイン名を右クリックしてプロパティを開きます。
1. 信頼タブで「新しい信頼」を作成します。以下の選択肢がでない場合はしばらく待ってから作業を実施してください。

    |項目|値|備考|
    |---|---|---|
    |信頼の名前|japan.example.com||
    |信頼の種類|フォレストの信頼||
    |信頼の方向|双方向||
    |信頼を作成する対象|このドメインのみ||
    |出力方向の信頼認証レベル|フォレスト全体の認証||
    |信頼パスワード|（任意）||
    |出力方向の信頼を確認しますか?|確認しない||
    |入力方向の信頼を確認しますか?|確認しない||

作成した信頼はPowerShellで確認できます。

```powershell
Get-ADTrust -Filter *
```

#### JAPANドメイン

japan.example.comのドメインコントローラーで以下の作業を実施します。

1. サーバーマネージャーの右上のツールから「Active Directory ドメインと信頼関係」を開きます。
1. 左のペインでドメイン名を右クリックしてプロパティを開きます。
1. 信頼タブで「新しい信頼」を作成します。以下の選択肢がでない場合はしばらく待ってみて下さい。

    |項目|値|備考|
    |---|---|---|
    |信頼の名前|resource.example.com||
    |信頼の種類|フォレストの信頼||
    |信頼の方向|双方向||
    |信頼を作成する対象|このドメインのみ||
    |出力方向の信頼認証レベル|フォレスト全体の認証||
    |信頼パスワード|（任意）||
    |出力方向の信頼を確認しますか?|確認しない||
    |入力方向の信頼を確認しますか?|確認しない||

作成した信頼はPowerShellで確認できます。

```powershell
Get-ADTrust -Filter *
```

### メンバーインスタンスでのリモートデスクトップ接続の許可

AD環境であっても、メンバーインスタンスではAdministratorsグループやRemote Desktop Usersグループはローカルグループであり、マシンごとに異なるグループです。
メンバーインスタンスに`Administrator@resource.example.com`でRDPし、`user1@japan.example.com`のリモートデスクトップ接続を許可します。

1. スタートボタンを右クリックして「システム」を選択します。
1. 左のメニューで「リモートの設定」をクリックします。
1. 「リモート」タブで「ユーザーの選択」をクリックし、`user1@japan.example.com`を追加します。見つからないときはしばらく待ってみて下さい。

### メンバーインスタンスへのログイン確認

踏み台インスタンスから、メンバーインスタンスに`user1@japan.example.com`でRDPできることを確認します。

## FSxのデプロイ

（ここは以下のようにCDKでもできるが、時間がかかるので、GUIを使った方がよいかも）

resource.example.comに接続するファイルシステムのデプロイにはドメンコントローラーのIPアドレスと、接続に使用するユーザーとパスワードが必要です。
`cdk.context.json`に記載します。本来は権限を絞ったユーザーで接続するべきですが、検証なのでAdministratorを使います。

FSxリソースをデプロイします（かなり時間がかかります）。

```shell
cdk deploy *ResourceDomainFSxStack --require-approval never
```

### マウント確認

FSxのファイルシステムのDNS名を確認します。

```shell
aws fsx describe-file-systems | \
  jq -r '.FileSystems[] |
           select( .Tags ) | 
           select( [ select( .Tags[].Value | test("ResourceDomainFSxStack") ) ] | length > 0 ) | 
           .DNSName'
```

メンバーインスタンスに`user1@japan.example.com`でRDPし、FSxのファイルシステムにネットワークドライブを割り当てます。
`¥`と`\`の違い（Windows上では同じに見える）でエラーになっていたことがあったので注意。マネジメントコンソールで「Attach」ボタンを押してコマンドを取得した方が確実です。

```powershell
net use z: \\<DNS名>\share
```

## DFSの設定

- [PowerShellでDFSの環境を構築する](https://blog.shibata.tech/entry/2018/07/18/000420)

JAPANのドメインコントローラーをDFS名前空間サーバーとして設定します。

DFSの構成に必要な機能をインストールします。

```powershell
Import-Module ServerManager
Get-WindowsFeature
Install-WindowsFeature FS-DFS-Namespace, FS-DFS-Replication, RSAT-DFS-Mgmt-Con
Get-WindowsFeature
```

DFSルートを作ります。
名前空間サーバー上にある共有フォルダに対してNew-DfsnRootコマンドを実行します。

```powershell
# 名前空間の作成
$DFSRootPath = '\\japan.example.com\Public'
$DFSRootTarget = 'C:\DFSRoots\Public'
$DFSRootSharedPath = "\\$(hostname)\Public"
# 共有フォルダを作成
mkdir $DFSRootTarget
New-SmbShare –Name 'Public' –Path $DFSRootTarget -FullAccess everyone
# DFSルート作成
New-DfsnRoot -Path $DFSRootPath -Type DomainV2 -TargetPath $DFSRootSharedPath
```

JAPANのドメインコントローラーにログインして確認します。

## Amazon FSx CLIの実行

- [Getting Started with the Amazon FSx CLI for Remote Management on PowerShell](https://docs.aws.amazon.com/fsx/latest/WindowsGuide/remote-pwrshell.html) 

FSxのPowerShell用のエンドポイントを確認します。

```
aws fsx describe-file-systems | jq -r '.FileSystems[].WindowsConfiguration.RemoteAdministrationEndpoint'
```

RESOURCEのドメインコントローラーにAdministratorでログインし、PowerShellを実行します。

```powershell
enter-pssession -ComputerName amznfsxjcdhtmu2.resource.example.com -ConfigurationName FsxRemoteAdmin -sessionoption (New-PSSessionOption -uiCulture "en-US")
```

クォータを有効にします。単位はバイトです。

```powershell
Enable-FSxUserQuotas -Track -DefaultLimit 2000000 -DefaultWarningLimit 1000000
Enable-FSxUserQuotas -Enforce -DefaultLimit 4000000 -DefaultWarningLimit 3000000
```

設定を確認します。

```powershell
Get-FSxUserQuotaSettings
```

```powershell
[amznfsxjcdhtmu2.resource.example.com]: PS>Get-FSxUserQuotaSettings

DefaultWarningLimit DefaultLimit State
------------------- ------------ -----
            3000000      4000000 Enforce

```

user1@japan.example.comのクオータを設定します。

```shell
Set-FSxUserQuotas -Domain "resource.example.com" -Name "user1" -Limit 60000 -WarningLimit 40000
Set-FSxUserQuotas -Domain "resource.example.com" -Name "group1" -Limit 60000 -WarningLimit 40000
Set-FSxUserQuotas -Domain "japan.example.com" -Name "user1" -Limit 60000 -WarningLimit 40000
```

設定を確認します。

```powershell
[amznfsxjcdhtmu2.resource.example.com]: PS>Get-FSxUserQuotaEntries


WarningLimit  : 40000
DiskSpaceUsed : 0
QuotaVolume   : Win32_LogicalDisk (DeviceID = "D:")
Limit         : 60000
Status        : OK
User          : Win32_Account (Name = "user1", Domain = "RESOURCE")

WarningLimit  : 40000
DiskSpaceUsed : 61440
QuotaVolume   : Win32_LogicalDisk (DeviceID = "D:")
Limit         : 60000
Status        : Exceeded
User          : Win32_Account (Name = "user1", Domain = "JAPAN")

WarningLimit  : 40000
DiskSpaceUsed : 0
QuotaVolume   : Win32_LogicalDisk (DeviceID = "D:")
Limit         : 60000
Status        : OK
User          : Win32_Account (Name = "group1", Domain = "RESOURCE")


```