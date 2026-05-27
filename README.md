1、注册微软hotmail邮箱
2、注册tailscale账号，并绑定hotmail邮箱
3、注册render账号，网站地址：https://render.com/
      	3.1 登录Render 并连接GitHub，github代码仓库地址：https://github.com/lshwei000-jpg/wechattrans
	3.2 创建Web Service
		3.2.1 进入Dashboard 后，点击右上角醒目的蓝色New +按钮
		3.2.2 在下拉菜单中选择Web Service（Web 服务）
		3.2.3 此时页面会显示Connect a repository （连接仓库），在列表中找到你刚刚上传了代码的那个GitHub 仓库，点击它旁边的Connect按钮
	3.3 配置服务参数（核心步骤）
		3.3.1 Name : 给你的服务起个名字（例如：my-tailscale-proxy）
		3.3.2 Region : 保持默认即可（比如Oregon 或Frankfurt）
		3.3.3 Branch : 保持默认（通常是main或master）
		3.3.4 Runtime（运行环境） : 【最关键的一步】一定要把默认的Python 改选为Docker
		3.3.5 Instance Type（实例类型） : 往下滚动，务必勾选Free（$0/month 免费层）
	3.4 注入Tailscale 密钥（高级设置）
		在点击最下方的创建按钮之前，先往下拉
		3.4.1 找到并展开Advanced（高级设置）按钮
		3.4.2 找到Environment Variables（环境变量）区域，点击Add Environment Variable
		3.4.3 填入以下内容
			Key :TAILSCALE_AUTHKEY
			Value : 填入你在Tailscale 官网申请的、以tskey-auth-开头的密钥
	3.5 检查所有配置无误后，点击最下方的Create Web Service按钮
访问前端：在Render 页面左上角（项目名称下方），你会看到一个形如https://xxxx.onrender.com的免费公网网址

4、保活
	如果这个网页长时间（通常是15 分钟内）没有任何人去点击访问，容器就会进入“休眠/睡着”状态。
	影响：当你休眠后再次去访问它的xxxx.onrender.com网页时，它需要大约30 秒到1 分钟的时间来“重新苏醒”（Cold Start）。不过不用担心，只要有人一访问，它就会立刻重新拉起你的Flask 网页和后端的Tailscale 隧道

	注册Cronjob，网站地址：https://cron-job.org/en/
	使用在Render 页面左上角（项目名称下方），会看到一个形如https://xxxx.onrender.com的免费公网网址，Cronjob设置每10min或者13min访问一次，防止睡眠
	选择“自订”，填入*/10 8-22 * * *，代表每天8点到22点每隔10min唤醒一次，防止休眠；
