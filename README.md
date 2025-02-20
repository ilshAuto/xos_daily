# ILSH XOS V1.0

## 社区支持
- 💬 官方：[空投信息、脚本TG频道](https://t.me/ilsh_auto)
- 🐦 最新公告：[我们的推特](https://x.com/hashlmBrian)

## 功能特点
- 自动签到
- 自动绑定sol地址(使用acc中的助记词生成sol链钱包)
- ！！由于签到需要绑定x、dc，需要在网站绑定完再使用本代码

## ⚠️ 重要安全警告

**涉及敏感信息操作须知：**

1. 本系统需处理钱包助记词等敏感信息
2. **必须**在可信的本地环境运行
3. 禁止将助记词上传至任何网络服务

## 🚀 快速开始
！！！！必须启动WALLET SERVER：

本代码分js、python两部分。
js：用于evm、sol，代码：查看WALLET_SERVER: https://github.com/ilshAuto/wallet_server/releases/tag/wallet_server
python：用于与xos服务端交互
### Python 环境配置


```` 
安装Python依赖
pip install -r requirements.txt
准备账户配置文件
"助记词----代理地址"
示例配置内容：
angry list clock vacuum dizzy phrase... ---- socks5://user:pass@127.0.0.1:1080
运行主程序
python xos_daily_check.py
````
## 支持开发

☕ 如果您觉得这个工具有帮助，可以通过发送 USDT 来支持开发:

- 网络: TRC20
- 地址: `TAiGnbo2isJYvPmNuJ4t5kAyvZPvAmBLch`

## 免责声明

本工具仅用于区块链技术研究，使用者应自行承担以下风险：

1. 本地环境安全导致的资产损失
2. 自动化操作触发的风控机制
3. 网络延迟造成的交易失败
4. 其他不可预见的链上风险