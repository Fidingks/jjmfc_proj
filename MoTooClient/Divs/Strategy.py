from facecat import * 
current_directory = os.getcwd()
DB_PATH = f'{current_directory}/data/user.db' 

# x是allStrategy的宽度
def ChangeLocation(views, x):
    button_width = 200
    button_height = 300
    spacing = 10

    buttons_per_row = (x ) // (button_width + 20) + 1
    row = 0  # 当前行
    col = 0  # 当前列
    for view in views:
        button_x = col * (button_width + spacing) + spacing
        button_y = row * (button_height + spacing) + spacing
        view.location = FCPoint(button_x, button_y)
        col += 1
        if col >= buttons_per_row:  # 如果当前列数超出每行按钮数，换到下一行
            col = 0
            row += 1
       
         
#图层
class StrategyDiv(FCView):
    def __init__(self):
        super().__init__()
        self.strategy = {}
        self.status = ""
        self.size = FCSize(200, 300)
        self.viewType = "strategyDiv"
        self.backColor = "rgb(0,0,0)"
        self.cornerRadius = 10
        self.onPaint = self.onPaintStrategyDiv
        self.onPaintBorder = self.onPaintStrategyDivBorder
        self.borderWidth = 2
        self.borderColor = "rgb(255, 255, 255)"
        self.onMouseWheel = self.scroll

    def unsubscribe(self):
        pass

    def subscribe(self):
        pass

    def onPaintStrategyDiv(self, div, paint, clipRect):
        strategy = div.strategy
        if div.backColor != "none":
            paint.fillRoundRect(div.backColor, 0, 0, div.size.cx, div.size.cy, div.cornerRadius)
        drawFont = "Default,14"
        paint.drawLine("rgb(255,255,255)", 1.5, 0, 180, 8, 190, 20)
        paint.drawLine("rgb(255,255,255)", 1.5, 0, 190, 8, 180, 20)
        paint.drawText(str(strategy[2]), "rgb(175,196,228)", drawFont, 60,  1)
        arr1 = ["当前价格","策略类型","策略摘要","通知等级","通知冷却","通知次数"]
        arr2 = ["9.88",str(strategy[4]),strategy[6],str(strategy[7]),str(strategy[8]) + "分钟",str(strategy[11]) + "/" + str(strategy[10])]
        for i in range(0, len(arr1)):
            paint.drawText(arr1[i], "rgb(175,196,228)", drawFont, 6,  30 + 40 * i)
            paint.drawText(arr2[i], "rgb(255,82,82)", drawFont, 72,  30 + 40 * i)

    def onPaintStrategyDivBorder(self, view, paint, clipRect):
        if view.viewType == "strategyDiv":
            paint.drawRoundRect(view.borderColor, view.borderWidth, 0, 0, 0, view.size.cx, view.size.cy, view.cornerRadius)
            paint.drawEllipse("rgb(255,0,0)", 3, 0, 0, 0, 5, 5)
        drawDivScrollBar(view, paint, clipRect)
    # 修改鼠标滚轮实现
    def scroll(self, view, mp, buttons, clicks, delta):
        if view.viewType == "strategyDiv":
            view = view.parent
        elif view.viewType == "div":
            pass
        oldScrollV = view.scrollV
        if delta > 0:
            oldScrollV -= 100
        elif delta < 0:
            oldScrollV += 100
        contentHeight = getDivContentHeight(view)
        if contentHeight < view.size.cy:
            view.scrollV = 0
        else:
            if oldScrollV < 0:
                oldScrollV = 0
            elif oldScrollV > contentHeight - view.size.cy:
                oldScrollV = contentHeight - view.size.cy
            view.scrollV = oldScrollV
        invalidateView(view)

