# encoding: UTF-8

"""
这里的Demo是一个最简单的策略实现，并未考虑太多实盘中的交易细节，如：
1. 委托价格超出涨跌停价导致的委托失败
2. 委托未成交，需要撤单后重新委托
3. 断网后恢复交易状态
4. 等等
这些点是作者选择特意忽略不去实现，因此想实盘的朋友请自己多多研究CTA交易的一些细节，
做到了然于胸后再去交易，对自己的money和时间负责。
也希望社区能做出一个解决了以上潜在风险的Demo出来。
"""


from ctaBase import *
from ctaTemplate import CtaTemplate


########################################################################
class DoubleEmaDemo(CtaTemplate):
    """双指数均线策略Demo"""
    className = 'DoubleEmaDemo'
    author = u'用Python的交易员'
    
    # 策略参数
    fastK = 0.9     # 快速EMA参数
    slowK = 0.1     # 慢速EMA参数
    initDays = 10   # 初始化数据所用的天数
    
    # 策略变量
    bar = None
    barMinute = EMPTY_STRING
    
    fastMa = []             # 快速EMA均线数组
    fastMa0 = EMPTY_FLOAT   # 当前最新的快速EMA
    fastMa1 = EMPTY_FLOAT   # 上一根的快速EMA

    slowMa = []             # 与上面相同
    slowMa0 = EMPTY_FLOAT
    slowMa1 = EMPTY_FLOAT
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'fastK',
                 'slowK']    
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'fastMa0',
               'fastMa1',
               'slowMa0',
               'slowMa1']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DoubleEmaDemo, self).__init__(ctaEngine, setting)
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略初始化')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略停止')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute
        
        if tickMinute != self.barMinute:    
            if self.bar:
                self.onBar(self.bar)
            
            bar = CtaBarData()              
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange
            
            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice
            
            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime    # K线的时间设为第一个Tick的时间
            
            # 实盘中用不到的数据可以选择不算，从而加快速度
            #bar.volume = tick.volume
            #bar.openInterest = tick.openInterest
            
            self.bar = bar                  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute     # 更新当前的分钟
            
        else:                               # 否则继续累加新的K线
            bar = self.bar                  # 写法同样为了加快速度
            
            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 计算快慢均线
        if not self.fastMa0:        
            self.fastMa0 = bar.close
            self.fastMa.append(self.fastMa0)
        else:
            self.fastMa1 = self.fastMa0
            self.fastMa0 = bar.close * self.fastK + self.fastMa0 * (1 - self.fastK)
            self.fastMa.append(self.fastMa0)
            
        if not self.slowMa0:
            self.slowMa0 = bar.close
            self.slowMa.append(self.slowMa0)
        else:
            self.slowMa1 = self.slowMa0
            self.slowMa0 = bar.close * self.slowK + self.slowMa0 * (1 - self.slowK)
            self.slowMa.append(self.slowMa0)
            
        # 判断买卖
        crossOver = self.fastMa0>self.slowMa0 and self.fastMa1<self.slowMa1     # 金叉上穿
        crossBelow = self.fastMa0<self.slowMa0 and self.fastMa1>self.slowMa1    # 死叉下穿
        
        # 金叉和死叉的条件是互斥
        # 所有的委托均以K线收盘价委托（这里有一个实盘中无法成交的风险，考虑添加对模拟市价单类型的支持）
        if crossOver:
            # 如果金叉时手头没有持仓，则直接做多
            if self.pos == 0:
                self.buy(bar.close, 1)
            # 如果有空头持仓，则先平空，再做多
            elif self.pos < 0:
                self.cover(bar.close, 1)
                self.buy(bar.close, 1)
        # 死叉和金叉相反
        elif crossBelow:
            if self.pos == 0:
                self.short(bar.close, 1)
            elif self.pos > 0:
                self.sell(bar.close, 1)
                self.short(bar.close, 1)
                
        # 发出状态更新事件
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    
########################################################################################
## 基于tick级别细粒度撤单追单测试demo

class OrderManagementDemo(CtaTemplate):
    """追撤单策略Demo"""
    className = 'OrderManagementDemo'
    author = u'用Python的交易员'
    
    # 策略参数

    initDays = 10   # 初始化数据所用的天数
    
    # 策略变量
    bar = None
    barMinute = EMPTY_STRING
    
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(OrderManagementDemo, self).__init__(ctaEngine, setting)
		
	self.lastOrder = None
        self.orderType = ''
	
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略初始化')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略停止')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

	# 建立不成交买单测试单	
	if self.lastOrder == None:
	    self.buy(tick.lastprice - 10.0, 1)

	# CTA委托类型映射
        if self.lastOrder != None and self.lastOrder.direction == u'多' and self.lastOrder.offset == u'开仓':
            self.orderType = u'买开'

        elif self.lastOrder != None and self.lastOrder.direction == u'多' and self.lastOrder.offset == u'平仓':
            self.orderType = u'买平'

        elif self.lastOrder != None and self.lastOrder.direction == u'空' and self.lastOrder.offset == u'开仓':
            self.orderType = u'卖开'

        elif self.lastOrder != None and self.lastOrder.direction == u'空' and self.lastOrder.offset == u'平仓':
            self.orderType = u'卖平'
		
	# 不成交，即撤单，并追单
        if self.lastOrder != None and self.lastOrder.status == u'未成交':

            self.cancelOrder(self.lastOrder.vtOrderID)
            self.lastOrder = None
        elif self.lastOrder != None and self.lastOrder.status == u'已撤销':
	# 追单并设置为不能成交
            
            self.sendOrder(self.orderType, self.tick.lastprice - 10, 1)
            self.lastOrder = None
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
	pass
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        self.lastOrder = order
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
########################################################################################
## 基于tick级别策略测试demo

class ChasingTickDemo(CtaTemplate):
    """策略名称：追涨Tick示例；
    策略思想：连续3笔tick买一价大于上一笔tick的买一价，买入；固定止赢和固定止损；
    使用方法：1、将此段代码加入ctaDemo.py文件；2、修改CTA_setting.json文件内容,配置股指IF1604；  3、在ctaSetting.py增加策略信息；
    编写时间：20160322，这只是一个示例，切勿实盘"""

    className = 'ChasingtickDemo'
    author = u'王衣谷'

    # 策略参数
    takeProfitPoint = 2  #止赢点数
    stopLossPoint = 1   #止损点数
    # 策略变量

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(ChasingTickDemo, self).__init__(ctaEngine, setting)

        self.lastOrder = None
        self.lastTrade = None
        self.tickList = [] #初始一个tick列表
        self.bType = 0 #买的状态，1表示买开委托状态，0表示非买开委托状态.目的是判断当前委托的状态，不要发生重复发单的事情
        self.sType = 0 #买的状态，1表示卖开委托状态，0表示非卖开委托状态

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'追涨Tick演示策略初始化')

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'追涨Tick演示策略启动')
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'追涨Tick演示策略停止')
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        #当新tick来的时候进行数据保存，保存4个tick的数据，
        self.tickList.append(tick)    #往列表后面增加新tick数据
        if len(self.tickList) > 4:   #如果数据长度大于4，则要进行删除动作
            del self.tickList[0]     #老数据从列表头部删掉

        #开单条件：连续3笔tick买一价大于上一笔tick的买一价，买入；反之卖出
        isBuySign = 0
        isShortSign = 0
        if len(self.tickList)>=4:
            isBuySign   = self.tickList[3].bidPrice1 > self.tickList[2].bidPrice1 and self.tickList[2].bidPrice1 > self.tickList[1].bidPrice1 and  self.tickList[1].bidPrice1 > self.tickList[0].bidPrice1
            isShortSign = self.tickList[3].askPrice1 < self.tickList[2].askPrice1 and self.tickList[2].askPrice1 < self.tickList[1].askPrice1 and  self.tickList[1].askPrice1 < self.tickList[0].askPrice1
        #开多单
        if isBuySign:
            # 如果买开时手头没有持仓，则直接对价做多
            if self.pos == 0 and self.bType == 0 and self.sType == 0:
                self.buy(tick.askPrice1, 1)
                self.bType = 1
                self.writeCtaLog(u'直接多开，买开价：'+str(tick.askPrice1))
            # 如果有空头持仓，则先平空，再做多
            elif self.pos < 0 and self.bType == 0:
                self.cover(tick.askPrice1, 1)
                self.sType = 0
                self.buy(tick.askPrice1, 1)
                self.bType = 1
                self.writeCtaLog(u'先空平再多开，买开价：'+str(tick.askPrice1))
        # 卖开和买开相反
        elif isShortSign:
            if self.pos == 0 and self.bType == 0 and self.sType == 0:
                self.short(tick.bidPrice1, 1)
                self.sType = 1
                self.writeCtaLog(u'直接空开，卖开价：'+str(tick.bidPrice1))
            elif self.pos > 0 and self.sType == 0:
                self.sell(tick.bidPrice1, 1)
                self.bType = 0
                self.short(tick.bidPrice1, 1)
                self.sType = 1
                self.writeCtaLog(u'先多平再空开，卖开价：'+str(tick.bidPrice1))

        # 固定止赢处理
        self.fixedTakeProfit()
        # 固定止损处理
        self.fixedStopLoss()

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onTrade
        self.lastTrade = trade

    #----------------------------------------------------------------------
    def fixedTakeProfit(self):
        """固定止赢处理,以股指示例，2个点止赢"""
        if self.bType == 1 and self.pos > 0:
            if self.tickList[3].lastPrice - self.lastTrade.price > self.takeProfitPoint: #如果多单赢利大于2个点
                self.sell(self.tickList[3].bidPrice1, 1)
                self.bType = 0
                self.writeCtaLog(u'多单固定止盈,--平仓价：' + str(self.tickList[3].bidPrice1) + u'--赢利点数：' + str(self.tickList[3].bidPrice1-self.lastTrade.price))
        elif self.sType == 1 and self.pos < 0:
            if self.lastTrade.price - self.tickList[3].lastPrice > self.takeProfitPoint: #如果空单赢利大于2个点
                self.cover(self.tickList[3].askPrice1, 1)
                self.sType = 0
                self.writeCtaLog(u'空单固定止盈,--平仓价：' + str(self.tickList[3].askPrice1) + u'--赢利点数：' + str(self.lastTrade.price-self.tickList[3].askPrice1) )

    #----------------------------------------------------------------------
    def fixedStopLoss(self):
        """固定止损处理,以股指示例，1个点止损"""
        if self.bType == 1 and self.pos > 0:
            if  self.lastTrade.price - self.tickList[3].lastPrice > self.stopLossPoint: #如果多单亏损大于1个点
                self.sell(self.tickList[3].bidPrice1, 1)
                self.bType = 0
                self.writeCtaLog(u'多单固定止损,--平仓价：' + str(self.tickList[3].bidPrice1) + u'--亏损点数：' + str(self.tickList[3].bidPrice1-self.lastTrade.price))
        elif self.sType == 1 and self.pos < 0:
            if self.tickList[3].lastPrice - self.lastTrade.price > self.stopLossPoint: #如果空单亏损大于1个点
                self.cover(self.tickList[3].askPrice1, 1)
                self.sType = 0
                self.writeCtaLog(u'空单固定止损,--平仓价：' + str(self.tickList[3].askPrice1) + u'--亏损点数：' + str(self.lastTrade.price-self.tickList[3].askPrice1) )
