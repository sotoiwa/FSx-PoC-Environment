## DFS

（以下の手順はMADの配下にDFSを立てる手順なので実施しない）

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
DirectoryId=$(aws ds describe-directories | 
                jq -r '.DirectoryDescriptions[] |
                         select( .Name == "corp.example.com" ) |
                         .DirectoryId')
KeyName=$(cat cdk.context.json | jq -r '.key_name')
SecurityGroup=$(aws ec2 describe-security-groups | 
                  jq -r '.SecurityGroups[] |
                           select ( .GroupName | test("InternalSecurityGroup") ) |
                           .GroupId')
Subnets=( $(aws ec2 describe-subnets | 
              jq -r '.Subnets[] |
                       select( .Tags ) | 
                       select( [ select( .Tags[].Value | test("Isolated") ) ] | length > 0 ) | 
                       .SubnetId') )
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
