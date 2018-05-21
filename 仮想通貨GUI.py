import sys
import _thread as thread
import threading
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QApplication, QWidget, QFrame, QPushButton, QLabel, QLineEdit, QComboBox
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import time
from datetime import datetime
from time import sleep
from zaifapi.impl import ZaifPublicApi, ZaifFuturesPublicApi, ZaifLeverageTradeApi
import pybitflyer

#変数、リスト
da = []
time_list = [] #時間
time_list_ref = [] #参照時間
price_list = [] #zaifのBTC価格
price_list2 = [] #bitflayerのBTC価格
swap_list = [] #取引指標(swap)
list = [] #各リストの一時保存用
bids_list = [] #板の怪情報
asks_list = [] #板の売り情報
zaif_key = "" #zaifでの取引に必要なAPIキー
zaif_secret = "" #zaifでの取引に必要なシークレットAPIキー
zaif_LevaTrade = ZaifLeverageTradeApi(zaif_key, zaif_secret)
zaif_future = ZaifFuturesPublicApi()
zaif = ZaifPublicApi()
bf_key = "" #bitflayerでの取引に必要なAPIキー
bf_secret = "" #bitflayerでの取引に必要なシークレットAPIキー
bfapi = pybitflyer.API(api_key=bf_key, api_secret=bf_secret)

class BarPlot():
    def __init__(self, parent=None):
        #取得データ描画のため、キャンバスとグラフを用意
        self.dpi = 100
        self.fig = Figure((14.4, 12), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)  # pass a figure to the canvas
        self.canvas.setParent(parent)

        self.axes = self.fig.add_axes([0.04, 0.6, 0.52, 0.35]) #main chart
        self.axes2 = self.fig.add_axes([0.04, 0.06, 0.52, 0.23]) #swap chart
        self.axes3 = self.fig.add_axes([0.04, 0.33, 0.52, 0.23]) #delta chart
        self.axes4 = self.fig.add_axes([0.59, 0.55, 0.1, 0.4]) #zaif bord
        self.axes5 = self.fig.add_axes([0.73, 0.55, 0.1, 0.4])  # zaif bord

        self.data = []

    def plot_list(self):
        #実際に描画するデータの取得及び、加工
        #zaifとitflayerの時間に対するBTCの価格を取得し、時間-価格、時間-取引指標(swap rate)、取引予約-価格のデータを作る
        y = zaif.last_price('btc_jpy')["last_price"]  #zaif BTCの現物価格
        y2 = (bfapi.ticker(product_code = "BTC_JPY"))["best_bid"] #bitflayerの現物価格
        time_list_ref.append(time.time()) #時間幅参照
        time_list.append(datetime.today())  # time_list
        price_list.append(y)  #zaif price_list
        price_list2.append(y2) #bf price list


        # swap_list
        if time_list_ref[-1] - time_list_ref[0] > 3600:
            while time_list[-1] - time_list[0] > 3600:  # 現在時刻から1時間以内の要素のみを残す
                del time_list_ref[0]
                del time_list[0]
                del price_list[0]
                del price_list2[0]

        index = price_list[-1] #BTC現物の価格(本来は一時間当たりの平均価格だが、)

        # zaif 先物取引の板情報を取得
        depth = zaif_future.depth(group_id=1, currency_pair='btc_jpy')
        bids_list = depth['bids']
        asks_list = depth['asks']
        bids_sum = 0
        bids_amounts = 0
        asks_sum = 0
        asks_amounts = 0

        # 売買板平均価格を計算する
        # 10btcまでの平均価格を採用（一日の取引量に応じて加重平均をとる範囲が1~10BTCで変動する）
        # 買い板平均価格の算出
        for i in range(len(bids_list)):
            bids_sum += bids_list[i][0] * bids_list[i][1]
            bids_amounts += bids_list[i][1]
            if bids_amounts >= 10:
                delta_amounts = bids_amounts - 10
                bids_amounts -= delta_amounts  # 買い高量10
                bids_sum -= bids_list[i][0] * delta_amounts
                bids_ave = bids_sum / bids_amounts  # 買い板平均価格(10btc)
                break

        # 売り板平均価格の算出
        for i in range(len(asks_list)):
            asks_sum += asks_list[i][0] * asks_list[i][1]
            asks_amounts += asks_list[i][1]
            if asks_amounts >= 10:
                delta_amounts = asks_amounts - 10
                asks_amounts -= delta_amounts  # 売り高量10
                asks_sum -= asks_list[i][0] * delta_amounts
                asks_ave = asks_sum / asks_amounts  # 売り板平均価格(10btc)
                break

        b_ave = bids_sum / bids_amounts
        a_ave = asks_sum / asks_amounts

        if index > b_ave and b_ave > a_ave:
            b_swap = (1 - (b_ave / index)) * 100

        if index > a_ave and a_ave > b_ave:
            b_swap = (1 - (a_ave / index)) * 100

        else:
            b_swap = 0

        swap_list.append(b_swap)
        return (time_list, price_list, price_list2, swap_list)

    def bord_inf(self):
        dp = zaif.depth("btc_jpy")
        dp_bid = dp["bids"]
        dp_ask = dp["asks"]

        bord_prices = []
        bord_amounts = []

        #売買板情報を板情報から10件表示、大きな注文を確認
        for i in range(10):
            bord_prices.append(dp_bid[i][0])
            bord_prices.insert(0, dp_ask[i][0])
            bord_amounts.append(dp_bid[i][1])
            bord_amounts.insert(0, -(dp_ask[i][1]))

        return(bord_prices, bord_amounts)

    def on_draw(self):
        #グラフを表示する下準備
        self.axes.clear()
        self.axes2.clear()
        self.axes3.clear()
        self.axes4.clear()
        self.axes5.clear()
        self.axes.grid()
        self.axes2.grid()
        self.axes3.grid()
        self.axes4.grid()
        self.axes5.grid()

        #plot_listで用意した表示したい値をプロットできる形に直す
        #listは一時的な値の置き場所
        list = self.plot_list()
        x = list[0] #時間
        y = list[1] #zaifのBTC価格
        y2 = list[2] #bitflayerのBTC価格
        y3 = list[3] #swaoの値
        delta = [y - y2 for (y, y2) in zip(y, y2)] #zaifとbtcの価格差
        list = self.bord_inf()
        bord_prices = list[0] #直近の取引成立価格
        bord_amounts = list[1] #上の取引量

        self.axes.plot(x, y, marker="o", color="b", linestyle="-", label="zaif")
        self.axes.plot(x, y2, marker="o", color="r", linestyle="-", label="bitflyer")
        self.axes2.plot(x, y3, marker="o", color="b", linestyle="-", label="swap")
        self.axes2.set_ylim(-3.5, 3.5)
        self.axes2.set_ylim(-3.5, 3.5)
        self.axes3.plot(x, delta, color="black", linestyle="-", label="zaif")
        self.axes4.plot(bord_amounts ,bord_prices , color="black", linestyle="-")

        self.canvas.draw()
        sleep(1)
        thread.start_new_thread(self.on_draw, ())

class AppForm(QMainWindow): #GUI上に各種操作取り付け
    def __init__(self, master=None):
        QMainWindow.__init__(self, master)
        QMainWindow.resize(self, 1920, 1200)

        self.creat_main_window()
        self.barplot.on_draw()

    def creat_main_window(self):
        #様々なWidgetの設定
        self.main_frame = QWidget()
        self.barplot = BarPlot(self.main_frame)
        # set layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.barplot.canvas)  # add canvas to the layout
        self.main_frame.setLayout(vbox)
        # set widget
        self.setCentralWidget(self.main_frame)
        #graph label
        timelabel = QLabel("Time(day h:m)", self.main_frame)
        timelabel.setFont(QFont("", 20))
        timelabel.setGeometry(550, 1010, 180, 40)
        swaplabel = QLabel("swap", self.main_frame)
        swaplabel.setFont(QFont("", 16))
        swaplabel.setGeometry(10, 710, 180, 40)
        pricelabel = QLabel("yen/btc", self.main_frame)
        pricelabel.setFont(QFont("", 16))
        pricelabel.setGeometry(10, 20, 180, 40)
        deltalabel = QLabel("delta", self.main_frame)
        deltalabel.setFont(QFont("", 16))
        deltalabel.setGeometry(10, 430, 180, 40)

        ###zaif frame###
        zaif_frame = QFrame(self)
        zaif_frame.setGeometry(1100, 550, 270, 600)
        zaif_frame.setStyleSheet("background-color: rgb(200, 200, 200)")
        # transaction form name
        zaif_label = QLabel("Zaif", zaif_frame)
        zaif_label.setFont(QFont("", 20))
        zaif_label.setGeometry(100, 0, 120, 40)
        # bid and ask label
        bid_label = QLabel("amount", zaif_frame)
        bid_label.setFont(QFont("", 16))
        bid_label.setGeometry(10, 60, 70, 40)
        ask_label = QLabel("price", zaif_frame)
        ask_label.setFont(QFont("", 16))
        ask_label.setGeometry(10, 120, 70, 40)
        # inputform
        self.amount = QLineEdit("", zaif_frame)
        self.amount.setStyleSheet("background-color: rgb(255, 255, 255)")
        self.amount.setFont(QFont("", 16))
        self.amount.setGeometry(100, 65, 100, 30)
        self.input_price = QLineEdit("", zaif_frame)
        self.input_price.setStyleSheet("background-color: rgb(255, 255, 255)")
        self.input_price.setFont(QFont("", 16))
        self.input_price.setGeometry(100, 125, 100, 30)
        # transaction button
        bid_button = QPushButton("bid", zaif_frame)
        bid_button.setFont(QFont("", 20))
        bid_button.setGeometry(65, 200, 150, 80)
        bid_button.setStyleSheet("background-color: rgb(200, 80, 20)")
        ask_button = QPushButton("ask", zaif_frame)
        ask_button.setFont(QFont("", 20))
        ask_button.setGeometry(65, 300, 150, 80)
        ask_button.setStyleSheet("background-color: rgb(20, 50, 200)")
        bid_button.clicked.connect(self.thread1)
        ask_button.clicked.connect(self.thread2)
        #Levarage
        self.combo = QComboBox(zaif_frame)
        self.combo.setGeometry(210, 35, 50, 30)
        self.combo.addItem("1")
        self.combo.addItem("2")
        self.combo.addItem("3")
        self.combo.addItem("4")
        self.combo.addItem("5")
        self.combo.addItem("10")
        Leva_label = QLabel("Levarage", zaif_frame)
        Leva_label.setFont(QFont("", 12))
        Leva_label.setGeometry(200, 10, 70, 30)

        Leva_label = QLabel("Levarage", zaif_frame)
        Leva_label.setFont(QFont("", 12))
        Leva_label.setGeometry(200, 10, 70, 30)

        ###bitflyer frame###
        bfframe = QFrame(self)
        bfframe.setGeometry(1371, 550, 270, 600)
        bfframe.setStyleSheet("background-color: rgb(200, 200, 200)")
        # transaction form name
        bf_label = QLabel("BitFlyer", bfframe)
        bf_label.setFont(QFont("", 20))
        bf_label.setGeometry(100, 0, 120, 50)
        # bid and ask label
        bid_label = QLabel("amount", bfframe)
        bid_label.setFont(QFont("", 16))
        bid_label.setGeometry(10, 60, 70, 40)
        ask_label = QLabel("price", bfframe)
        ask_label.setFont(QFont("", 16))
        ask_label.setGeometry(10, 120, 70, 40)
        # inputform
        self.bfamount = QLineEdit("", bfframe)
        self.bfamount.setStyleSheet("background-color: rgb(255, 255, 255)")
        self.bfamount.setFont(QFont("", 16))
        self.bfamount.setGeometry(100, 65, 100, 30)
        self.bfprice = QLineEdit("", bfframe)
        self.bfprice.setStyleSheet("background-color: rgb(255, 255, 255)")
        self.bfprice.setFont(QFont("", 16))
        self.bfprice.setGeometry(100, 125, 100, 30)
        # transaction button
        bid_button = QPushButton("bid", bfframe)
        bid_button.setFont(QFont("", 20))
        bid_button.setGeometry(65, 200, 150, 80)
        bid_button.setStyleSheet("background-color: rgb(200, 80, 20)")
        ask_button = QPushButton("ask", bfframe)
        ask_button.setFont(QFont("", 20))
        ask_button.setGeometry(65, 300, 150, 80)
        ask_button.setStyleSheet("background-color: rgb(20, 50, 200)")
        bid_button.clicked.connect(self.thread3)
        ask_button.clicked.connect(self.thread4)

        ###coin check frame###
        ccframe = QFrame(self)
        ccframe.setGeometry(1642, 550, 270, 600)
        ccframe.setStyleSheet("background-color: rgb(200, 200, 200)")
        # transaction form name
        cc_label = QLabel("CoinCheck", ccframe)
        cc_label.setFont(QFont("", 20))
        cc_label.setGeometry(100, 0, 120, 50)
        # bid and ask label
        bid_label = QLabel("amount", ccframe)
        bid_label.setFont(QFont("", 16))
        bid_label.setGeometry(10, 60, 70, 40)
        ask_label = QLabel("price", ccframe)
        ask_label.setFont(QFont("", 16))
        ask_label.setGeometry(10, 120, 70, 40)
        # inputform
        self.ccamount = QLineEdit("", ccframe)
        self.ccamount.setStyleSheet("background-color: rgb(255, 255, 255)")
        self.ccamount.setFont(QFont("", 16))
        self.ccamount.setGeometry(100, 65, 100, 30)
        self.ccprice = QLineEdit("", ccframe)
        self.ccprice.setStyleSheet("background-color: rgb(255, 255, 255)")
        self.ccprice.setFont(QFont("", 16))
        self.ccprice.setGeometry(100, 125, 100, 30)
        # transaction button
        bid_button = QPushButton("bid", ccframe)
        bid_button.setFont(QFont("", 20))
        bid_button.setGeometry(65, 200, 150, 80)
        bid_button.setStyleSheet("background-color: rgb(200, 80, 20)")
        ask_button = QPushButton("ask", ccframe)
        ask_button.setFont(QFont("", 20))
        ask_button.setGeometry(65, 300, 150, 80)
        ask_button.setStyleSheet("background-color: rgb(20, 50, 200)")
        bid_button.clicked.connect(self.thread5)
        ask_button.clicked.connect(self.thread6)

        ###account###
        accountframe = QFrame(self)
        accountframe.setGeometry(1642, 10, 270, 539)
        accountframe.setStyleSheet("background-color: rgb(200, 200, 200)")
        # label
        accoutlabel = QLabel("account(所持資産など)追加予定", accountframe)
        accoutlabel.setFont(QFont("", 14))
        accoutlabel.setGeometry(10, 0, 300, 40)

    #zaif bid process
    def thread1(self):
        threading.Thread(target=self.zaif_bid_process).start()
    def zaif_bid_process(self):
        n = int(self.amount.text()) #amount
        m = int(self.input_price.text()) #price
        l = int(self.combo.currentText()) #levarage
        #zaif_LevaTrade.trade(currency_pair="btc_jpy", action="bid", price=k, amount=m, Levarage=l)
        print('zaif: ' + "レバレッジ " + str(l) + "価格" + str(n) + "、数量" + str(m) + ' 円買い')
    # zaif ask process
    def thread2(self):
        threading.Thread(target=self.zaif_ask_process).start()
    def zaif_ask_process(self):
        n = int(self.amount.text())  # amount
        m = int(self.input_price.text())  # price
        l = int(self.combo.currentText())  # levarage
        #zaif_LevaTrade.trade(currency_pair="btc_jpy", action="ask", price=m, amount=n, Levarage=l)
        print('zaif: ' + "レバレッジ " + str(l) + "価格" + str(n) + "、数量" + str(m) + ' 円売り')
    #bf bid process(取引プログラムは未実装)
    def thread3(self):
        threading.Thread(target=self.bf_bid_process).start()
    def bf_bid_process(self):
        n = int(self.bfamount.text())  # amount
        m = int(self.bfprice.text())  # price
        # zaif_Trade.trade(currency_pair="btc_jpy", action="ask", price)
        print('bf: ' + "価格" + str(n) + "、数量" + str(m) + ' 円買い')
    #bf ask process(取引プログラムは未実装)
    def thread4(self):
        threading.Thread(target=self.bf_ask_process).start()
    def bf_ask_process(self):
        n = int(self.bfamount.text())  # amount
        m = int(self.bfprice.text())  # price
        # zaif_Trade.trade(currency_pair="btc_jpy", action="ask", price)
        print('bf: ' + "価格" + str(n) + "、数量" + str(m) + ' 円売り')
    #cc bid process(取引プログラムは未実装)
    def thread5(self):
        threading.Thread(target=self.cc_bid_process).start()
    def cc_bid_process(self):
        n = int(self.ccamount.text())  # amount
        m = int(self.ccprice.text())  # price
        # zaif_Trade.trade(currency_pair="btc_jpy", action="ask", price)
        print('cc: ' + "価格" + str(n) + "、数量" + str(m) + ' 円買い')
    #cc trade process(取引プログラムは未実装)
    def thread6(self):
        threading.Thread(target=self.cc_ask_process).start()
    def cc_ask_process(self):
        n = int(self.ccamount.text())  # amount
        m = int(self.ccprice.text())  # price
        # zaif_Trade.trade(currency_pair="btc_jpy", action="ask", price)
        print('cc: ' + "価格" + str(n) + "、数量" + str(m) + ' 円売り')

def main(args):
    app = QApplication(args)
    form = AppForm()
    form.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    try:
        main(sys.argv)
    except:
        print("板情報の取得に失敗")