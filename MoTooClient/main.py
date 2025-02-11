# -*- coding:utf-8 -*-
#! python3
from facecat import *
import json
#这里可能需要pip install requests
import requests
from requests.adapters import HTTPAdapter
from Divs.LatestDiv import drawLatestDiv, getPriceColor
from Divs.Strategy import *
from Divs.ControlPanel import *
from datetime import datetime
import ast
import threading
import json
import asyncio
import websockets
import time
current_directory = os.getcwd()
DB_PATH = f'{current_directory}/data/user.db' 
latestDataStr = ""
current_strategy = []

class WebSocketClient:
    def __init__(self, server_url, on_message_callback=None):
        """
        WebSocket 客户端初始化
        :param server_url: 服务端 WebSocket URL
        :param on_message_callback: 接收到消息时的回调函数
        """
        self.url = server_url
        self.connection = None
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.on_message_callback = on_message_callback  # 收到消息时的回调函数

    def start(self):
        """启动 WebSocket 客户端并在独立线程中运行"""
        print("启动 WebSocket 客户端...")
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        # 等待连接建立
        time.sleep(1)

    def _run(self):
        """运行 asyncio 事件循环"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())
        self.loop.run_forever()

    async def connect(self):
        """连接到服务端 WebSocket 并处理消息"""
        try:
            self.connection = await websockets.connect(self.url)
            print(f"成功连接到服务器: {self.url}")
            asyncio.create_task(self.handle_messages())  # 启动消息处理任务
            self.send_message("get_all_strategy", {})
        except Exception as e:
            print(f"连接失败: {e}")

    async def handle_messages(self):
        """处理从服务端接收到的消息"""
        while True:
            try:
                message = await self.connection.recv()
                data = json.loads(message)
                if self.on_message_callback:
                   self.on_message_callback(data)
            except websockets.ConnectionClosed:
                print("连接已关闭，尝试重新连接...")
                break

    def send_message(self, action, data):
        """
        向服务端发送消息
        :param action: 指令类型（如 "get_strategy", "add_strategy" 等）
        :param data: 数据字典
        """
        if self.connection:
            message = {
                "action": action,
                "data": data
            }
            # 使用 asyncio 的线程安全方法在事件循环中发送消息
            asyncio.run_coroutine_threadsafe(self.connection.send(json.dumps(message)), self.loop)
            print(f"已发送消息: {message}")
        else:
            print("连接尚未建立，无法发送消息")

    def stop(self):
        """关闭 WebSocket 连接并停止事件循环"""
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread.is_alive():
            self.thread.join()
        print("WebSocket 客户端已停止")

# 示例回调函数
def process(data):
	print(f"回调: {data}")
	if data["action"] == "get_all_strategy":
		message = data.get("message", "")
		parsed_message = ast.literal_eval(message)  # 使用 literal_eval 解析
		StrategyCallBack(parsed_message)
	if data["action"] == "start_strategy":
		print("启动 或者 停止 这个策略")
	if data["action"] == "add_strategy":
		message = data.get("message", "")
		parsed_message = ast.literal_eval(message)  # 使用 literal_eval 解析
		StrategyCallBack(parsed_message)

#开始Http请求
#url:地址
#callBack回调
def startGetRequest(url, callBack, tag):
	data = FCData()
	data.key = url
	data.callBack = callBack
	try:
		s = requests.Session()
		s.mount('http://', HTTPAdapter(max_retries=3))
		response = s.get(url)
		result = response.text
		data.success = True
		data.data = result
	except requests.exceptions.RequestException as e:
		data.success = False
		data.data = str(e)
	data.tag = tag
	gPaint.addData(data)
	user32.PostMessageW(gPaint.hWnd, 0x0401, 0, 0)

def startPostRequest(url, params, callBack, tag):
	data = FCData()
	data.key = url
	data.callBack = callBack
	try:
		s = requests.Session()
		s.mount('http://', HTTPAdapter(max_retries=3))
		response = s.post(url, json = params)
		result = response.text
		data.success = True
		data.data = result
	except requests.exceptions.RequestException as e:
		data.success = False
		data.data = str(e)
	data.tag = tag
	gPaint.addData(data)
	user32.PostMessageW(gPaint.hWnd, 0x0401, 0, 0)

#进行Http请求
#url:地址
#callBack回调
def getRequest(url, callBack, tag):
	thread = threading.Thread(target=startGetRequest, args=(url, callBack, tag))
	thread.start()

def postRequest(url, payload, callBack, tag):
	thread = threading.Thread(target=startPostRequest, args=(url, payload, callBack, tag))
	thread.start()

#历史数据回调
def historyDataCallBack(data):
	if data.success:
		mychart = data.tag[0]
		chart = data.tag[1]
		code = data.tag[2]
		intCycle = data.tag[3]
		result = data.data
		dataList = []
		strs = result.split("\r\n")
		chart.firstOpen = 0
		if intCycle == 0:
			fStrs = strs[0].split(" ")
			if len(fStrs) >= 3:
				chart.firstOpen = float(fStrs[2])
		for i in range(2, len(strs)):
			subStrs = strs[i].split(",")
			if len(subStrs) >= 7:
				data = SecurityData()
				if intCycle < 1440:
					dateStr = subStrs[0] + " " + subStrs[1][0:2] + ":" + subStrs[1][2:4] + ":00"
					data.open = float(subStrs[2])
					data.high = float(subStrs[3])
					data.low = float(subStrs[4])
					data.close = float(subStrs[5])
					data.volume = float(subStrs[6])
					date_obj = datetime.strptime(dateStr, "%Y-%m-%d %H:%M:%S")
					data.date = time.mktime(date_obj.timetuple())
					if intCycle == 0 and data.volume > 0:
						chart.lastValidIndex = len(dataList)
						if chart.firstOpen == 0:
							chart.firstOpen = data.close
				else:
					data.open = float(subStrs[1])
					data.high = float(subStrs[2])
					data.low = float(subStrs[3])
					data.close = float(subStrs[4])
					data.volume = float(subStrs[5])
					dateStr = subStrs[0]
					date_obj = datetime.strptime(dateStr, "%Y-%m-%d")
					data.date = time.mktime(date_obj.timetuple())
				dataList.append(data)
		if intCycle == 0:
			chart.autoFillHScale = True
			chart.cycle = "trend"
		elif intCycle < 1440:
			chart.cycle = "minute"
		else:
			chart.cycle = "day"
		chart.datas = dataList
		maxVisibleRecord = getChartMaxVisibleCount(chart, chart.hScalePixel, getChartWorkAreaWidth(chart))
		chart.lastVisibleIndex = len(chart.datas) - 1
		if maxVisibleRecord > len(chart.datas):
			chart.firstVisibleIndex = 0
		else:
			chart.firstVisibleIndex = chart.lastVisibleIndex - maxVisibleRecord + 1
		resetChartVisibleRecord(chart)
		checkChartLastVisibleIndex(chart)
		calcChartIndicator(chart)
		invalidateView(chart)


#请求历史数据
def queryHistoryData(mychart, chart, code):
	strCycle = mychart.exAttributes["cycle"]
	intCycle = int(strCycle)
	url = "http://110.42.188.197:9968/quote?func=getkline&code=" + code +  "&cycle=" + strCycle + "&count=500"
	if intCycle == 0:
		url = "http://110.42.188.197:9968/quote?func=getkline&code=" + code +  "&cycle=0&count=240"
	tag = []
	tag.append(mychart)
	tag.append(chart)
	tag.append(code)
	tag.append(intCycle)
	getRequest(url, historyDataCallBack, tag)
	
#请求最新数据
def queryNewData(code):
	url = "http://110.42.188.197:9968/quote?func=getnewdata&codes=" + code
	tag = []
	getRequest(url, newDataCallBack, tag)

#最新数据回调
def newDataCallBack(data):
	if data.success:
		global latestDataStr
		result = data.data
		latestDataStr = result
		invalidate(gPaint)

#板块数据回调
def queryPriceCallBack(data):
	if data.success:
		global gridStocks
		result = data.data
		strs = result.split("\r\n")
		for i in range(0, len(strs)):
			subStrs = strs[i].split(",")
			if len(subStrs) >= 15:
				row = FCGridRow()
				gridStocks.rows.append(row)
				cell1 = createGridCell(gridStocks)
				cell1.value = i
				row.cells.append(cell1)

				cell2 = createGridCell(gridStocks)
				cell2.value = subStrs[0]
				cell2.textColor = "rgb(194,151,18)"
				row.cells.append(cell2)

				cell3 = createGridCell(gridStocks)
				cell3.value = subStrs[1]
				row.cells.append(cell3)

				close = float(subStrs[2])
				high = float(subStrs[3])
				low =  float(subStrs[4])
				lastClose = float(subStrs[8])
				cell4 = createGridCell(gridStocks)
				cell4.value = toFixed(close, 2)
				cell4.textColor = getPriceColor(close, lastClose)
				row.cells.append(cell4)
				diff = 0
				if lastClose > 0:
					diff = 100 * (close - lastClose) / lastClose
				cell5 = createGridCell(gridStocks)
				cell5.value = toFixed(diff, 2) + "%"
				cell5.textColor = getPriceColor(diff, 0)
				row.cells.append(cell5)

				cell6 = createGridCell(gridStocks)
				cell6.value = toFixed(close - lastClose, 2)
				cell6.textColor = getPriceColor(close, lastClose)
				row.cells.append(cell6)

				volume = float(subStrs[6])
				amount = float(subStrs[7])
				cell7 = createGridCell(gridStocks)
				cell7.value = toFixed(volume / 100 / 10000, 2) + "万"
				row.cells.append(cell7)

				cell8 = createGridCell(gridStocks)
				cell8.value = toFixed(amount / 100000000, 2) + "亿"
				row.cells.append(cell8)

				cell9 = createGridCell(gridStocks)
				cell9.value = toFixed(float(subStrs[12]), 2)
				row.cells.append(cell9)

				cell10 = createGridCell(gridStocks)
				cell10.value = toFixed(float(subStrs[11]), 2)
				row.cells.append(cell10)

				diff2 = 0
				if lastClose > 0:
					diff2 = 100 * (high - lastClose) / lastClose - 100 * (low - lastClose) / lastClose
				cell11 = createGridCell(gridStocks)
				cell11.value = toFixed(diff2, 2) + "%"
				row.cells.append(cell11)

				cell12 = createGridCell(gridStocks)
				cell12.value = toFixed(float(subStrs[13]), 2)
				row.cells.append(cell12)

				marketValue = float(subStrs[9]) * close
				cell13 = createGridCell(gridStocks)
				cell13.value = toFixed(marketValue / 100000000, 2) + "亿"
				row.cells.append(cell13)

				flowValue = float(subStrs[10]) * close
				cell14 = createGridCell(gridStocks)
				cell14.value = toFixed(flowValue / 100000000, 2) + "亿"
				row.cells.append(cell14)

				cell15 = createGridCell(gridStocks)
				cell15.value = ""
				row.cells.append(cell15)

				upperLimit = float(subStrs[14])
				lowerLimit = float(subStrs[15])
				cell16 = createGridCell(gridStocks)
				cell16.value = toFixed(upperLimit, 2)
				cell16.textColor = getPriceColor(1, 0)
				row.cells.append(cell16)

				cell17 = createGridCell(gridStocks)
				cell17.value = toFixed(lowerLimit, 2)
				cell17.textColor = getPriceColor(0, 1)
				row.cells.append(cell17)

				cell18 = createGridCell(gridStocks)
				cell18.value = ""
				row.cells.append(cell18)

				cell19 = createGridCell(gridStocks)
				cell19.value = ""
				row.cells.append(cell19)

				cell20 = createGridCell(gridStocks)
				cell20.value = ""
				row.cells.append(cell20)

				cell21 = createGridCell(gridStocks)
				cell21.value = ""
				row.cells.append(cell21)

				cell22 = createGridCell(gridStocks)
				cell22.value = ""
				row.cells.append(cell22)
		invalidateView(gridStocks)

#查询报价数据
def queryPrice(codes):
	url = "http://110.42.188.197:9968/quote?func=price&count=500&codes=" + codes
	tag = []
	getRequest(url, queryPriceCallBack, tag)

#策略数据回调
def StrategyCallBack(data):
	allStrategy = findViewByName("allStrategy", gPaint.views)
	allStrategy.views = []
	for result in data:
		strategyDiv = StrategyDiv()
		strategyDiv.strategy =list(result)
		strategyDiv.viewName = result[1] # strategy_id
		strategyDiv.status = result[14] # active
		if result[14] == 1: # active
			strategyDiv.borderColor = "rgb(184,255,137)"
		else:
			strategyDiv.status = 0
		strategyDiv.onClick = onClickStrategyDiv
		addViewToParent(strategyDiv, allStrategy)
	ChangeLocation(allStrategy.views, allStrategy.size.cx)
	invalidate(gPaint)


#绘制视图
#view:视图
#paint:绘图对象
#clipRect:区域
def onPaint(view, paint, clipRect):
	if view.viewType == "latestdiv":
		drawLatestDiv(view, paint, latestDataStr, clipRect)
	elif view.viewType == "control":
		drawControlPanel(view, paint, current_strategy, clipRect)
	elif view.viewName == "allStrategy":
		x = view.size.cx
		ChangeLocation(view.views, x)
	else:
		onPaintDefault(view, paint, clipRect)

#黑色风格
def toBlack_Chart(chart, index):
	chart.paint.defaultUIStyle = "dark"
	chart.backColor = "rgb(0,0,0)"
	chart.borderColor = "none"
	chart.textColor = "rgb(175,196,228)"
	chart.scaleColor = "rgb(75,75,75)"
	chart.crossTipColor = "rgb(50,50,50)"
	chart.crossLineColor = "rgb(100,100,100)"
	chart.gridColor = "rgb(50,50,50)"
	if index > 0:
		chart.upColor = "rgb(186,56,18)"
		chart.downColor = "rgb(31,182,177)"
	else:
		chart.upColor = "rgb(255,82,82)"
		chart.downColor = "rgb(46,255,50)"		
	chart.barStyle = "rect2"
	chart.candleStyle = "rect2"
	chart.trendColor = "rgb(255,255,255)"
	chart.hScaleTextColor = "rgb(194,151,18)"
	chart.vScaleTextColor = "rgb(194,151,18)"
	chart.indicatorColors = []
	chart.indicatorColors.append("rgb(255,255,255)")
	chart.indicatorColors.append("rgb(255,255,0)")
	chart.indicatorColors.append("rgb(255,0,255)")
	chart.indicatorColors.append("rgb(255,0,0)")
	chart.indicatorColors.append("rgb(0,255,255)")
	chart.indicatorColors.append("rgb(0,255,0)")
	chart.indicatorColors.append("rgb(255,255,0)")
	chart.indicatorColors.append("rgb(255,255,255)")



#查找同类型视图
def findViewsByType(findType, views, refViews):
	size = len(views)
	for i in range(0, size):
		view = views[i]
		if view.viewType == findType:
			refViews.append(view)
		elif len(view.views) > 0:
			findViewsByType(findType, view.views, refViews)

#点击单元格
def onClickGridCell(grid, row, gridColumn, cell, firstTouch, firstPoint, secondTouch, secondPoint, clicks):
	code = row.cells[1].value
	name = row.cells[2].value
	for i in range(0, len(findMyCharts)):
		myChart = findMyCharts[i]
		chart = charts[i]
		chart.text = code + " " + name
		queryHistoryData(myChart, chart, code)
		if i >= 2:
			break
	queryNewData(code)
	invalidate(grid.paint)

#视图的鼠标点击方法
#view 视图
#mp 坐标
#buttons 按钮 0未按下 1左键 2右键
#clicks 点击次数
#delta 滚轮值
def onClick(view, firstTouch, firstPoint, secondTouch, secondPoint, clicks):
	onClickDefault(view, firstTouch, firstPoint, secondTouch, secondPoint, clicks)
	if view.viewName.find("cycle,") == 0:
		strs = view.viewName.split(",")
		index = int(strs[1])
		cycleInt = int(strs[2])
		findMyCharts[index].exAttributes["cycle"] = str(cycleInt)
		queryHistoryData(findMyCharts[index], charts[index], charts[index].text.split(" ")[0])
	elif view.viewName == "allStrategy":
		print("点击策略试图")
		global current_strategy
		current_strategy = []
		drawControlPanelDefault(current_strategy)
		invalidate(gPaint)

def drawControlPanelDefault(strategy):
	view = findViewByName("control", gPaint.views)
	view.views = []
	addButton = FCButton()
	addButton.font = "Default,14"
	addButton.location = FCPoint(50,200)
	addViewToParent(addButton,  view)
	addButton.text = "添加策略"
	addButton.onClick = AddStrategyToAll

# 添加策略回调
def AddStrategyToAll(view, firstTouch, firstPoint, secondTouch, secondPoint, clicks):
	print("添加一个策略")
	tag = []
	payload = {
    "symbol": "btcusdt",
	"wallet": "FWnPy6eH9Y5DbPjui8ojCdwz5gv6WqzSK3hFc5ouct6C",
    "strategy_type": 0,
    "strategy": '{"up_over":"4500","down_under":"3000"}',
    "strategy_abstract": "涨破4500，跌破3000",
    "notify_level": 1,
    "notify_interval_time": 30,
    "total_notify_times": 3
	}
	ws_client.send_message("add_strategy", payload)


def ChangeStrategy(view, firstTouch, firstPoint, secondTouch, secondPoint, clicks):
	control_panel = view.parent
	symbol = control_panel.views[1].text
	strategy_type = control_panel.views[2].text
	strategy_id = control_panel.views[10].viewName[6:] 
	print(control_panel.views[10].viewName)
	strategy_abstract = control_panel.views[4].text
	up_over = control_panel.views[5].text
	down_under = control_panel.views[6].text
	notify_interval_time =  control_panel.views[7].text
	strategy = json.dumps({"up_over":up_over, "down_under":down_under})
	print("提交策略更改到数据库")
	payload = {"symbol": symbol,
    "strategy_id": strategy_id,
    "strategy_type": strategy_type,
    "strategy": strategy,
    "strategy_abstract": strategy_abstract,
    "notify_level": 1,
    "notify_interval_time": notify_interval_time,
    "total_notify_times": 3}
	ws_client.send_message("update_strategy", payload)
	strategyDiv = findViewByName(strategy_id, gPaint.views)
	strategyDiv.strategy[2] = symbol
	strategyDiv.strategy[6] = strategy_abstract
	strategyDiv.strategy[8] = notify_interval_time
	strategyDiv.strategy[5] = json.dumps({"up_over":up_over, "down_under":down_under})
	invalidate(gPaint)

def clickStartButton(view, firstTouch, firstPoint, secondTouch, secondPoint, clicks):
	StrategyDiv = findViewByName(view.viewName[5:], gPaint.views)
	if StrategyDiv.status == 0:
		print("运行策略")
		view.text = "停止策略"
		view.backColor = "rgb(180,0,0)"
		strategy_id = (StrategyDiv.strategy[1])
		StrategyDiv.borderColor = "rgb(184,255,137)"
		payload = {"strategy_id":strategy_id, "active":1}
		StrategyDiv.status = 1
		ws_client.send_message("start_strategy", payload)
	elif StrategyDiv.status == 1:
		view.backColor = "rgb(255,255,255)"
		StrategyDiv.borderColor = "rgb(255,255,255)"
		strategy_id = (StrategyDiv.strategy[1])
		payload = {"strategy_id":strategy_id, "active":0}
		# ws发送
		StrategyDiv.status = 0
		view.text = "运行策略"
		print("停止策略")
		ws_client.send_message("start_strategy", payload)
	invalidate(gPaint)
# 点击策略回调
def onClickStrategyDiv(view, firstTouch, firstPoint, secondTouch, secondPoint, clicks):
	x = firstPoint.x
	y = firstPoint.y
	if clicks == 2:
		if view.status == 1:
			view.unsubscribe()
		elif view.status == 0:
			view.subscribe()
		print("启动策略")
	elif clicks == 1:
		print(x)
		print(y)
		
		if 170 < x < 200 and 0 < y < 20:
			print("删除一个策略")
			ws_client.send_message("delete_strategy", {"strategy_id":view.viewName})
			removeViewFromParent(view, view.parent)
			# queryStrategy()
		elif True:
			control_panel = findViewByName("control", gPaint.views)
			control_panel.views = []
			comBox = FCComboBox()
			comBox.text = "加密货币"
			comBox.location = FCPoint(75, 30)
			addViewToParent(comBox, control_panel)
			for i in range(0,10):
				menuitem = FCMenuItem()
				menuitem.text = "加密货币" + str(i + 1)
				addMenuItem(menuitem, comBox)

			SymbolTextbox = FCTextBox()
			SymbolTextbox.location = FCPoint(75, 70)
			addViewToParent(SymbolTextbox, control_panel)
			SymbolTextbox.text = view.strategy[2] 

			TypeTextbox = FCTextBox()
			TypeTextbox.location = FCPoint(75, 110)
			addViewToParent(TypeTextbox, control_panel)
			TypeTextbox.text = str(view.strategy[4])

			AddTimeLabel = FCLabel()
			AddTimeLabel.textColor = "rgb(255,255,255)"
			AddTimeLabel.location = FCPoint(75, 150)
			addViewToParent(AddTimeLabel, control_panel)
			AddTimeLabel.text = str(view.strategy[13])

			AbstractTextbox = FCTextBox()
			AbstractTextbox.location = FCPoint(75, 190)
			addViewToParent(AbstractTextbox, control_panel)
			AbstractTextbox.text = str(view.strategy[6])

			UpOverTextbox = FCTextBox()
			UpOverTextbox.location = FCPoint(75, 230)
			addViewToParent(UpOverTextbox, control_panel)
			up_over = json.loads(view.strategy[5])["up_over"]
			UpOverTextbox.text = up_over

			DownUnderTextBox = FCTextBox()
			DownUnderTextBox.location = FCPoint(75, 270)
			addViewToParent(DownUnderTextBox, control_panel)
			down_under = json.loads(view.strategy[5])["down_under"]
			DownUnderTextBox.text = down_under

			IntervaltimeTextbox = FCTextBox()
			IntervaltimeTextbox.location = FCPoint(75, 310)
			addViewToParent(IntervaltimeTextbox, control_panel)
			IntervaltimeTextbox.text = str(view.strategy[8])


			NotifyLevelTexbox = FCTextBox()
			NotifyLevelTexbox.location = FCPoint(75, 350)
			addViewToParent(NotifyLevelTexbox, control_panel)
			NotifyLevelTexbox.text = str(view.strategy[7])

			NotifyTimesTexbox = FCLabel()
			NotifyTimesTexbox.location = FCPoint(75, 390)
			NotifyTimesTexbox.textColor ="rgb(255,255,255)"
			addViewToParent(NotifyTimesTexbox, control_panel)
			NotifyTimesTexbox.text = str(view.strategy[11]) + "/" + str(view.strategy[10])


			submit_change  = FCButton()
			submit_change.text = "提交更改"
			submit_change.viewName = "submit" + view.strategy[1]
			submit_change.location = FCPoint(50, 500)
			submit_change.onClick = ChangeStrategy
			addViewToParent(submit_change, control_panel)

			startButton = FCButton()
			if view.status == 1:
				startButton.text = "停止策略"
				startButton.backColor = "rgb(188,0,0)"
			elif view.status == 0:
				startButton.text = "运行策略"
			startButton.onClick = clickStartButton
			startButton.viewName = "start" + view.strategy[1]
			startButton.location = FCPoint(50, 550)
			addViewToParent(startButton, control_panel)
			global current_strategy
			current_strategy = view.strategy
			invalidate(gPaint)

#创建单元格
def createGridCell (grid):
	gridCell = FCGridCell()
	if grid.paint.defaultUIStyle == "dark":
		gridCell.backColor = "none"
		gridCell.borderColor = "none"
		gridCell.textColor = "rgb(175,196,228)"
	elif grid.paint.defaultUIStyle == "light":
		gridCell.backColor = "none"
		gridCell.borderColor = "none"
		gridCell.textColor = "rgb(0,0,0)"
	gridCell.font = "Default,13"
	return gridCell

#绘制横轴刻度的自定义方法
#chart:图表
#paint:绘图对象
#clipRect:裁剪区域
def drawChartHScale(chart, paint, clipRect):
	#判断数据是否为空
	if chart.datas != None and len(chart.datas) > 0 and chart.hScaleHeight > 0:
		if chart.cycle == "trend":
			times = []
			if chart.size.cx < 600:
				times.append(10 * 60 + 30)
				times.append(11 * 60 + 30)
				times.append(14 * 60)
			else:
				times.append(10 * 60)
				times.append(10 * 60 + 30)
				times.append(11 * 60)
				times.append(11 * 60 + 30)
				times.append(13 * 60 + 30)
				times.append(14 * 60)
				times.append(14 * 60 + 30)
			for i in range(chart.firstVisibleIndex, chart.lastVisibleIndex + 1):
				dateNum = chart.datas[i].date
				date = time.localtime(dateNum)
				hour = date.tm_hour
				minute = date.tm_min
				for j in range(0, len(times)):
					if times[j] == hour * 60 + minute:
						x = getChartX(chart, i)
						bBottom = chart.size.cy
						paint.drawLine(chart.scaleColor, 1, 0, x, bBottom - chart.hScaleHeight, x, bBottom - chart.hScaleHeight + 12)
						paint.drawLine(chart.gridColor, 1, 0, x, 0, x, bBottom - chart.hScaleHeight)
						xText = time.strftime("%H:%M", date)
						tSize = paint.textSize(xText, "Default,12")
						paint.drawText(xText, chart.hScaleTextColor, "Default,12", x - tSize.cx / 2, bBottom - chart.hScaleHeight / 2 - tSize.cy / 2)
						break
		elif chart.cycle == "minute":
			lastYear = 0
			lastDate2 = 0
			dLeft = chart.leftVScaleWidth
			i = chart.firstVisibleIndex
			while i <= chart.lastVisibleIndex:
				dateNum = chart.datas[i].date
				date = time.localtime(dateNum)
				year = date.tm_year
				xText = ""
				if year != lastYear:
					xText = time.strftime("%Y/%m/%d", date)
				else:
					xText = time.strftime("%m/%d", date)
				lastDate = time.localtime(lastDate2)
				if int(date.tm_year * 10000 + date.tm_mon * 100 + date.tm_mday) != int(lastDate.tm_year * 10000 + lastDate.tm_mon * 100 + lastDate.tm_mday):
					lastDate2 = dateNum
					lastYear = year
					tSize = paint.textSize(xText, "Default,12")
					x = getChartX(chart, i)
					dx = x + 2
					if dx > dLeft and dx + tSize.cx < chart.size.cx - chart.rightVScaleWidth - 5:
						bBottom = chart.size.cy
						paint.drawLine(chart.scaleColor, 1, 0, x, bBottom - chart.hScaleHeight, x, bBottom - chart.hScaleHeight + 12)
						paint.drawText(xText, chart.hScaleTextColor, "Default,12", dx, bBottom - chart.hScaleHeight / 2 - tSize.cy / 2)
						i = i + int((tSize.cx + chart.hScaleTextDistance) / chart.hScalePixel) + 1
				i = i + 1						
		else:
			drawLeft = chart.leftVScaleWidth #左侧起画点
			i = chart.firstVisibleIndex #开始索引
			lastYear = 0 #缓存年份，用于判断是否换年
			drawYearsCache = [] #实际绘制到图形上的年份文字
			lastTextRight = 0 #上个文字的右侧
			timeCache = [] #保存日期的缓存
			yearTextLeftCache = [] #绘制年文字的左侧位置缓存
			yearTextRightCache = [] #绘制年文字的右侧位置缓存
			textPadding = 5 #两个文字之间的最小间隔
			#逐步递增索引，先绘制年
			while i <= chart.lastVisibleIndex:
				dateObj = time.localtime(chart.datas[i].date) #将时间戳转换为time，并缓存到集合中
				timeCache.append(dateObj)
				year = dateObj.tm_year #从结构中获取年份			
				x = getChartX(chart, i) #获取索引对应的位置
				#判断是否换年，以及是否在绘图区间内
				if year != lastYear and x >= drawLeft and x < chart.size.cx - chart.rightVScaleWidth:
					month = dateObj.tm_mon #获取月的结构
					xText = str(year) #拼接要绘制的文字
					if month < 10:
						xText = xText + "/0" + str(month) #如果小于10月要补0
					else:
						xText = xText + "/" + str(month) #大于等于10月不用补0
					tSize = paint.textSize(xText, chart.font) #计算要绘制文字的大小
					paint.drawLine(chart.scaleColor, 1, 0, x, chart.size.cy - chart.hScaleHeight, x, chart.size.cy - chart.hScaleHeight + 8) #绘制刻度线
					#判断是否和上个文字重影
					if x - tSize.cx / 2 > lastTextRight + textPadding:
						paint.drawText(xText, chart.hScaleTextColor, "Default,12", x - tSize.cx / 2, chart.size.cy - chart.hScaleHeight + 8  - tSize.cy / 2 + 7) #绘制文字
						yearTextLeftCache.append(x - tSize.cx / 2) #将年文字的左侧位置缓存
						yearTextRightCache.append(x + tSize.cx / 2) #将年文字的右侧位置缓存
						drawYearsCache.append(year) #缓存要绘制的年
						lastTextRight = x + tSize.cx / 2 #缓存上个文字的右侧位置
					lastYear = year #记录上次绘制的年份
				i = i + 1	#索引累加	
			#绘制月份
			for m in range(0, len(drawYearsCache)):
				cacheYear = drawYearsCache[m] #从缓存中获取年份
				lastMonth = 0 #缓存月份，用于判断是否换月
				i = chart.firstVisibleIndex #重置开始索引
				lastTextRight = 0 #重置上个文字的右侧
				#逐步递增索引
				while i <= chart.lastVisibleIndex:
					dateObj = timeCache[i - chart.firstVisibleIndex] #从缓存中获取time
					year = dateObj.tm_year #从结构中获取年份
					#判断是否同一年	
					if cacheYear == year:
						month = dateObj.tm_mon #从结构中获取月份
						x = getChartX(chart, i)
						#判断是否换月，以及是否在绘图区间内
						if lastMonth != month and x >= drawLeft and x < chart.size.cx - chart.rightVScaleWidth:			
							xText = str(month) #获取绘制的月份文字
							tSize = paint.textSize(xText, chart.font) #计算要绘制文字的大小
							#判断是否和上个文字重影
							if x - tSize.cx / 2 > lastTextRight + textPadding:
								#判断是否和年的文字重影
								if (x - tSize.cx / 2 > yearTextRightCache[m] + textPadding) and ((m == len(drawYearsCache) - 1) or (m < len(drawYearsCache) - 1 and x + tSize.cx / 2 < yearTextLeftCache[m + 1] - textPadding)):
									paint.drawLine(chart.scaleColor, 1, 0, x, chart.size.cy - chart.hScaleHeight, x, chart.size.cy - chart.hScaleHeight + 6) #绘制刻度
									paint.drawText(xText, chart.hScaleTextColor, "Default,12", x - tSize.cx / 2, chart.size.cy - chart.hScaleHeight + 8  - tSize.cy / 2 + 7) #绘制文字
									lastTextRight = x + tSize.cx / 2 #缓存上个文字的右侧位置
							lastMonth = month #记录上次绘制的月份
					elif cacheYear < year:
						break #超过区间，退出循环
					i = i + 1	#索引累加

#消息循环
def WndProc(hwnd,msg,wParam,lParam):
	if msg == 0x0401:
		gPaint.dealData()
	return WndProcDefault(gPaint,hwnd,msg,wParam,lParam)

ws_client = WebSocketClient(server_url= "ws://localhost:8002/ws", on_message_callback=process)
ws_client.start()

gPaint = FCPaint() #创建绘图对象
gPaint.defaultUIStyle = "dark"
gPaint.onPaint = onPaint
gPaint.onClickGridCell = onClickGridCell
gPaint.onClick = onClick
gPaint.onPaintChartHScale = drawChartHScale

#gPaint.highQuanlity()
#gPaint.scaleFactorX = 1.33
#gPaint.scaleFactorY = 1.33
#初始化窗体
createMainWindow(gPaint, "facecat-py", WndProc)
# 打开并读取XML文件

xml = ""
with open(f'{current_directory}\\xml\\mainframe.xml', 'r', encoding='utf-8') as file:
    xml = file.read()


renderFaceCat(gPaint, xml)

# 绘制控制面板

drawControlPanelDefault(current_strategy)

gridStocks = findViewByName("gridStocks", gPaint.views)
for i in range(3, len(gridStocks.columns)):
	gridStocks.columns[i].cellAlign = "right"
gridStocks.selectedRowColor = "rgb(75,75,75)"
gridStocks.alternateRowColor = "rgb(25,25,25)"
queryPrice("all")
findMyCharts = []
charts = []
strCode = "600000.SH"
strName = "浦发银行"
findViewsByType("mychart", gPaint.views, findMyCharts)
for i in range(0, len(findMyCharts)):
	myChart = findMyCharts[i]
	splitDiv = FCSplitLayoutDiv()
	splitDiv.layoutStyle = "toptobottom"
	splitDiv.size = FCSize(400, 400)
	splitDiv.backColor = "none"
	splitDiv.borderColor = "none"
	splitDiv.dock = "fill"
	addViewToParent(splitDiv, myChart)

	topDiv = FCLayoutDiv()
	topDiv.backColor = "none"
	topDiv.borderColor = "none"
	topDiv.layoutStyle = "lefttoright"
	topDiv.showHScrollBar = False
	addViewToParent(topDiv, splitDiv)

	bottomDiv = FCDiv()
	bottomDiv.backColor = "none"
	bottomDiv.borderColor = "none"
	addViewToParent(bottomDiv, splitDiv)

	splitDiv.firstView = topDiv
	splitDiv.secondView = bottomDiv

	splitter = FCView()
	splitter.parent = splitDiv
	if gPaint.defaultUIStyle == "dark":
		splitter.backColor = "rgb(75,75,75)"
	elif gPaint.defaultUIStyle == "light":
		splitter.backColor = "rgb(150,150,150)"
	splitter.borderColor = "none"
	splitter.paint = gPaint
	splitDiv.views.append(splitter)
	splitDiv.splitter = splitter
	splitter.size = FCSize(400, 1)
	splitter.location = FCPoint(0, 30)
	if i == 0:
		splitter.location = FCPoint(0, 0)
		
	chart = FCChart()
	chart.leftVScaleWidth = 70
	chart.rightVScaleWidth = 70
	chart.vScaleDistance = 35
	chart.hScalePixel = 11
	chart.hScaleHeight = 30
	chart.candlePaddingTop = 30
	chart.candlePaddingBottom = 20
	chart.volPaddingTop = 20
	chart.volPaddingBottom = 0
	chart.vScaleDistance = 35
	chart.dock = "fill"
	chart.font = "Default,12"
	chart.candleDivPercent = float(myChart.exAttributes["candledivpercent"])
	chart.volDivPercent = float(myChart.exAttributes["voldivpercent"])
	chart.indDivPercent = 0
	chart.text = strCode + " " + strName
	strCycle = myChart.exAttributes["cycle"]
	intCycle = int(strCycle)
	if intCycle == 0:
		chart.text += " 分时"
	elif intCycle < 1440:
		chart.text += " " + str(intCycle) + "分钟"
	elif intCycle == 1440:
		chart.text += " 日线"
	elif intCycle == 10080:
		chart.text += " 周线"
	elif intCycle == 43200:
		chart.text += " 月线"
	chart.allowDragChartDiv = True
	charts.append(chart)
	addViewToParent(chart, bottomDiv)
	toBlack_Chart(chart, i)
	queryHistoryData(myChart, chart, strCode)
	cycles = []
	cycles.append("1")
	cycles.append("5")
	cycles.append("10")
	cycles.append("15")
	cycles.append("20")
	cycles.append("30")
	cycles.append("60")
	cycles.append("90")
	cycles.append("120")
	cycles.append("日")
	cycles.append("周")
	cycles.append("月")
	cycles.append("季")
	cycles.append("半")
	cycles.append("年")
	cyclesInts = []
	cyclesInts.append(1)
	cyclesInts.append(5)
	cyclesInts.append(10)
	cyclesInts.append(15)
	cyclesInts.append(20)
	cyclesInts.append(30)
	cyclesInts.append(60)
	cyclesInts.append(90)
	cyclesInts.append(120)
	cyclesInts.append(1440)
	cyclesInts.append(10080)
	cyclesInts.append(43200)
	cyclesInts.append(129600)
	cyclesInts.append(259200)
	cyclesInts.append(518400)
	for c in range(0, len(cycles)):
		cycleButton = FCButton()
		cycleButton.text = cycles[c]
		cycleButton.size = FCSize(27, 30)
		cycleButton.textColor = "rgb(200,200,200)"
		cycleButton.borderColor = "rgb(50,50,50)"
		cycleButton.backColor = "none"
		cycleButton.viewName = "cycle," + str(i) + "," + str(cyclesInts[c])
		addViewToParent(cycleButton, topDiv)
	comBox = FCComboBox()
	addViewToParent(comBox, chart)
	for i in range(0,10):
		menuitem = FCMenuItem()
		menuitem.text = "菜单项" + str(i + 1)
		addMenuItem(menuitem, comBox)
queryNewData(strCode)
updateViewDefault(gPaint.views)
showWindow(gPaint)