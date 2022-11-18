# import all libraries useful for this program
import string
from unicodedata import decimal
import pandas as pd  # pandas for manipulation of data
import math  # math for calculations
from yahoofinancials import YahooFinancials  # yahoofinancials for retrieving data
import datetime as dt  # datetime for retrieving current time
from flask import Flask  # flask for python web application
from decimal import Decimal
import babel.numbers

initial_capital = 10000

# these raw data is collected for further calculations in this program
all_tickers = ["VFINX", "VINEX", "VUSTX"]
def get_data():
    close_prices = pd.DataFrame()
    # get data of the recent years
    end_date = (dt.date.today()).strftime('%Y-%m-%d')
    beg_date = dt.date(1997, 12, 1).strftime('%Y-%m-%d')
    # to get data of a specific range, please replace the two lines above with: (example, the two lines below)
    # beg_date = dt.date(2014, 6, 30).strftime('%Y-%m-%d')
    # end_date = dt.date(2016, 6, 30).strftime('%Y-%m-%d')
    # VFINX:    Vanguard 500 Index Fund Investor Shares
    # VINEX:    Vanguard International Explorer
    # VUSTX:    Vanguard Long-term US Treasury
    # extracting stock data (historical close price) for the stocks identified
    for ticker in all_tickers:
        yahoo_financials = YahooFinancials(ticker)
        json_obj = yahoo_financials.get_historical_price_data(beg_date, end_date, "monthly")
        ohlv = json_obj[ticker]['prices']
        temp = pd.DataFrame(ohlv)[["formatted_date", "adjclose"]]
        if 'Date' in close_prices.columns and close_prices["Date"][0] < dt.datetime.strptime(temp["formatted_date"][0], '%Y-%m-%d'):
            close_prices["Date"] = pd.to_datetime(temp["formatted_date"])
        elif 'Date' not in close_prices.columns:
            close_prices["Date"] = pd.to_datetime(temp["formatted_date"])
        close_prices[ticker] = temp["adjclose"]
        close_prices.dropna(axis=0, inplace=True)
    return close_prices

data = get_data()  # "data" containing rows: "Date", "VFINX", "VINEX" and "VUSTX"

month1, month3, month6 = 1, 3, 6
data_columns = [f"{month1} mo. % rtn- VFINX", f"{month1} mo. % rtn- VINEX",
                f"{month1} mo. % rtn- VUSTX", f"{month3} mo. % rtn- VFINX",
                f"{month3} mo. % rtn- VINEX", f"{month3} mo. % rtn- VUSTX",
                f"{month6} mo. % rtn- VFINX", f"{month6} mo. % rtn- VINEX",
                f"{month6} mo. % rtn- VUSTX", "total % rtn- VFINX",
                "total % rtn- VINEX", "total % rtn- VUSTX"]
for data_column in data_columns: data[data_column] = 0.0
data["VFINX > VINEX"], data["VFINX > VUSTX"], data["VINEX > VUSTX"] \
    = False, False, False
data["Output"], data["Benchmark"] = "", float(0)

# calculate 1,3,6-monthly & total monthly returns of different indexes
for i in range(0, len(data["VFINX"] - 1)):  # for rows in data retrieved
    # calculate 1-monthly returns of different indexes
    for ticker in all_tickers:
        if (i - 1) < 0:  # entry 0 defined as 0.0
            data[f"{month1} mo. % rtn- " + ticker][i] = 0.0
        else:
            data[f"{month1} mo. % rtn- " + ticker][i] = "{0:.3f}".format((data[ticker][i] - data[ticker][i - 1]) / data[ticker][i - 1])
        # calculate 3-monthly returns of different indexes
        for n in [month3, month6]:
            if (i - (n - 1)) < 0:  # entry 0 defined as 0.0
                data[f"{n} mo. % rtn- " + ticker][i] = 0.0
            else:
                data[f"{n} mo. % rtn- " + ticker][i] = "{0:.3f}".format((data[ticker][i] - data[ticker][i - (n - 1)]) / \
                                                          data[ticker][i - (n - 1)])
    # calculate total % rtns of different indexes
    for ticker in all_tickers:
        data["total % rtn- " + ticker][i] = "{0:.3f}".format(data[f"{month1} mo. % rtn- " + ticker][i] + \
                                             data[f"{month3} mo. % rtn- " + ticker][i] + \
                                             data[f"{month6} mo. % rtn- " + ticker][i])
    # use total % rtns to generate conditional signals
    data["VFINX > VINEX"][i] = (data["total % rtn- VFINX"][i] >= data["total % rtn- VINEX"][i])
    data["VFINX > VUSTX"][i] = (data["total % rtn- VFINX"][i] >= data["total % rtn- VUSTX"][i])
    data["VINEX > VUSTX"][i] = (data["total % rtn- VINEX"][i] >= data["total % rtn- VUSTX"][i])

# remove first n1 values which are equal to 0
data = data[1:].reset_index(drop=True)
data["Benchmark"][0] = float(initial_capital / (data["VFINX"][0]) * data["VFINX"][0])

# change "Output" value depending out total % rtns
if data["VFINX > VINEX"][0]:
    data["Output"][0] = "VFINX" if 0 < data["total % rtn- VFINX"][0] else "VUSTX"
else:
    data["Output"][0] = "VINEX" if data["total % rtn- VINEX"][0] > 0 else "VUSTX"
# calculate benchmark values
for i in range(1, len(data["VFINX"] - 1)): 
    data["Benchmark"][i] = float(initial_capital / (data["VFINX"][0]) * (data["VFINX"][i]))

for i in range(1, len(data["VFINX"] - 1)):
    # different cases of signals
    if data["VFINX > VINEX"][i]:
        if data["total % rtn- VFINX"][i] > 0:
            data["Output"][i] = "Keep VFINX" \
                if data["Output"][i - 1] == "VFINX" or data["Output"][i - 1] == "Keep VFINX" else "VFINX"
        else:
            data["Output"][i] = "Keep VUSTX" \
                if data["Output"][i - 1] == "VUSTX" or data["Output"][i - 1] == "Keep VUSTX" else "VUSTX"
    else:
        if data["total % rtn- VINEX"][i] > 0:
            if data["Output"][i - 1] == "VINEX" or data["Output"][i - 1] == "Keep VINEX":
                data["Output"][i] = "Keep VINEX"
            else:
                data["Output"][i] = "VINEX"
        else:
            if data["Output"][i - 1] == "VUSTX" or data["Output"][i - 1] == "Keep VUSTX":
                data["Output"][i] = "Keep VUSTX"
            else:
                data["Output"][i] = "VUSTX"

# create new dataset ("buy_signals") with only buy signals (remove Keep signals)
buy_signals = data.drop(data[data.Output == "Keep VUSTX"].index).drop(data[data.Output == "Keep VFINX"].index) \
    .drop(data[data.Output == "Keep VINEX"].index).reset_index(drop=True)
    
# columns with qty amount to buy
bs_columns = ["Qty VUSTX", "Qty VFINX", "Qty VINEX", "VUSTX Buy Amount", "VUSTX Sell Amount", "VFINX Buy Amount",
              "VFINX Sell Amount", "VINEX Buy Amount", "VINEX Sell Amount", "Buy Amount", "Sell Amount",
              "P/L", "Cash Account", "realised_val"]
for bs_column in bs_columns: buy_signals[bs_column] = 0.0
for ticker in all_tickers:
    if buy_signals["Output"][0] == ticker:
        buy_signals["Qty " + ticker][0] = math.floor(initial_capital / buy_signals[ticker][0])
        buy_signals[ticker + " Buy Amount"][0] = buy_signals["Qty " + ticker][0] * buy_signals[ticker][0]
# total buy amount
buy_signals["Buy Amount"][0] = buy_signals["VUSTX Buy Amount"][0] + buy_signals["VFINX Buy Amount"][0] + \
                               buy_signals["VINEX Buy Amount"][0]
buy_signals["Cash Account"][0] = initial_capital - buy_signals["Buy Amount"][0]
# realised value is cash value of assets + cash account at hand
buy_signals["realised_val"][0] = buy_signals["Buy Amount"][0] + buy_signals["Cash Account"][0]
# buy and sell amount for individual assets
for i in range(1, len(buy_signals["Output"])):
    # sell amount for VUSTX
    for ticker in all_tickers:
        if buy_signals["Output"][i - 1] == ticker:
            buy_signals[ticker + " Sell Amount"][i] = buy_signals["Qty " + ticker][i - 1] * buy_signals[ticker][i]
    # total sell amount
    buy_signals["Sell Amount"][i] = buy_signals["VUSTX Sell Amount"][i] + buy_signals["VFINX Sell Amount"][i] + \
                                    buy_signals["VINEX Sell Amount"][i]
    for ticker in all_tickers:
        if buy_signals["Output"][i] == ticker:
            buy_signals["Qty " + ticker][i] = math.floor((buy_signals["Cash Account"][i - 1] +
                                                          buy_signals["Sell Amount"][i]) / buy_signals[ticker][i])
            buy_signals[ticker + " Buy Amount"][i] = buy_signals["Qty " + ticker][i] * buy_signals[ticker][i]
    # total buy amount
    buy_signals["Buy Amount"][i] = buy_signals["VUSTX Buy Amount"][i] + buy_signals["VFINX Buy Amount"][i] + \
                                   buy_signals["VINEX Buy Amount"][i]
    # cash account is the remaining balance after buying Whole shares
    buy_signals["Cash Account"][i] = buy_signals["Cash Account"][i - 1] - buy_signals["Buy Amount"][i] + \
                                     buy_signals["Sell Amount"][i]
    # calculate profit and loss
    buy_signals["P/L"][i] = Decimal(buy_signals["Sell Amount"][i] - buy_signals["Buy Amount"][i - 1])
    # realised value is cash value of assets + cash account at hand + profit/loss
    buy_signals["realised_val"][i] = Decimal(buy_signals["realised_val"][i - 1] + buy_signals["P/L"][i] + \
                                     buy_signals["Cash Account"][i])
buy_signals["Port_val"] = initial_capital
# calculate portfolio value which tracks the real time value of assets in the portfolio
for i in range(1, len(buy_signals["realised_val"])):
    buy_signals["Port_val"][i] = (buy_signals["Qty VUSTX"][i] * buy_signals["VUSTX"][i]) + \
                                 (buy_signals["Qty VFINX"][i] * buy_signals["VFINX"][i]) + \
                                 (buy_signals["Qty VINEX"][i] * buy_signals["VINEX"][i]) + \
                                 buy_signals["Cash Account"][i]

results = data.copy()
results_columns_1 = ["Qty VUSTX", "Qty VFINX", "Qty VINEX", "VUSTX Buy Amount", "VFINX Buy Amount", "VINEX Buy Amount",
                     "VUSTX Sell Amount", "VFINX Sell Amount", "VINEX Sell Amount", "Buy Amount", "Sell Amount",
                     "P/L", "realised_val", "Cash Account"]
results_columns_2 = ["Port_val", "PortMax", "DrawDown", "%change monthly", "%change benchmark", "Qty"]
for results_column in results_columns_1 + results_columns_2: 
    results[results_column] = 0.0
    
# copy buy signals to results
for i in range(0, len(buy_signals["Output"])):
    for j in range(0, len(data["Output"])):
        if buy_signals["Date"][i] == data["Date"][j]:
            for results_column_1 in results_columns_1:
                if isinstance(buy_signals[results_column_1][i], Decimal):
                    results[results_column_1][j] = buy_signals[results_column_1][i]
                else:
                    results[results_column_1][j] = buy_signals[results_column_1][i]

# fill in the gaps for the data in results, as buy_signals does not have all the rows
for i in range(1, len(results["realised_val"])):
    results["realised_val"][i] = results["realised_val"][i - 1] if results["realised_val"][i] == 0 \
        else results["realised_val"][i]
    for ticker in all_tickers:
        if results["Output"][i] == "Keep " + ticker:
            results["Qty " + ticker][i] = results["Qty " + ticker][i - 1]
        elif results["Output"][i] == ticker:
            results["Qty " + ticker] = results["Qty " + ticker]
        else:
            results["Qty " + ticker][i] = 0
    results["Qty"][i] = results["Qty VFINX"][i] + results["Qty VINEX"][i] + results["Qty VUSTX"][i]
    if results["Cash Account"][i] == 0 and i != 0:
        results["Cash Account"][i] = results["Cash Account"][i - 1]

results["Port_val"][0] = initial_capital
results["PortMax"][0] = initial_capital

for i in range(1, len(results["realised_val"])):
    results["Port_val"][i] = (results["Qty VUSTX"][i] * results["VUSTX"][i]) + (
            results["Qty VFINX"][i] * results["VFINX"][i]) + (results["Qty VINEX"][i] * results["VINEX"][i])
    curr_set2 = results["Port_val"][0:i + 1]
    results["PortMax"][i] = curr_set2.max()
    results["DrawDown"][i] = (results["Port_val"][i] - results["PortMax"][i]) / results["PortMax"][i]

# calculate percent changes in porfolio and benchmark on monthly basis
results["%change monthly"][0] = 0.0
results["%change benchmark"][0] = 0.0

for i in range(1, len(results["realised_val"])):
    # percent change daily
    results["%change monthly"][i] = (results["Port_val"][i] - results["Port_val"][i - 1]) / \
                                    results["Port_val"][i - 1]
    #    results["%change monthly"] = results["Port_val"].pct_change(1)
    results["%change benchmark"][i] = (results["Benchmark"][i] - results["Benchmark"][i - 1]) / \
                                      results["Benchmark"][i - 1]

message_text = "Current Action: " + str(results["Output"][len(results["Output"]) - 1]) 
message_text += '<br/> Quantity: ' + str(results["Qty"][len(results["Qty"]) - 1] )
message_text += '<br/> Buy Amount:  ' + str(results["Buy Amount"][len(results["Buy Amount"]) - 1])
message_text += '<br/> Portfolio Value:  ' + babel.numbers.format_currency(results["Port_val"][len(results["Port_val"]) - 1], "USD", locale="en_US")

data_attr = [["VFINX", "VINEX", "VUSTX", f"{month1} mo. % rtn- VFINX", f"{month1} mo. % rtn- VINEX",
              f"{month1} mo. % rtn- VUSTX", f"{month3} mo. % rtn- VFINX", f"{month3} mo. % rtn- VINEX",
              f"{month3} mo. % rtn- VUSTX", f"{month6} mo. % rtn- VFINX", f"{month6} mo. % rtn- VINEX",
              f"{month6} mo. % rtn- VUSTX", "total % rtn- VFINX", "total % rtn- VINEX", "total % rtn- VUSTX",
              "VFINX > VINEX", "VFINX > VUSTX", "VINEX > VUSTX", "Output", "Benchmark"],
             ["Qty VUSTX", "Qty VFINX", "Qty VINEX", "VUSTX Buy Amount", "VUSTX Sell Amount", "VFINX Buy Amount",
              "VFINX Sell Amount", "VINEX Buy Amount", "VINEX Sell Amount", "Buy Amount", "Sell Amount", "P/L",
              "Cash Account", "realised_val", "Output"],
             ["Qty VUSTX", "Qty VFINX", "Qty VINEX", "VUSTX Buy Amount", "VFINX Buy Amount", "VINEX Buy Amount",
              "VUSTX Sell Amount", "VFINX Sell Amount", "VINEX Sell Amount", "Buy Amount", "Sell Amount", "realised_val",
              "P/L", "Port_val", "Cash Account", "PortMax", "DrawDown", "%change monthly", "%change benchmark", "Qty"]]

def gen_data_str(dataSource, tableNumber):
    ret_str = "<table class='table table-hover'><tr><td>Date</td>"
    for element in data["Date"]:
        ret_str += "<td>" + str(element.strftime('%y-%m')) + "</td>"
    ret_str += "</tr>"
    
    attrIndex = 0
    # rows of different attributes of the table
    for attr in data_attr[tableNumber - 1]:
        ret_str += "<tr><td>" + str(attr) + "</td>"
        for element in dataSource[attr]:
            if '%' in attr:
                cellValue = Decimal(str(element))
                cellValue = cellValue*100
                className = "text-success" if cellValue > 0 else "text-danger"
                className += " table-success" if cellValue.compare(10) == 1 else ""
                className += " table-danger" if cellValue.compare(-10) == -1 else ""
                ret_str += f'<td class="{className}">' + '{:.2f}'.format(cellValue) + "%</td>"
            elif isinstance(element, float) and 'Benchmark' in attr:
                if (attrIndex > 0 and element < dataSource[attr][attrIndex-1]):
                    ret_str += "<td class='text-danger'>" + babel.numbers.format_currency(element, "USD", locale="en_US") + "</td>"
                else:
                    ret_str += "<td class='text-success'>" + babel.numbers.format_currency(element, "USD", locale="en_US") + "</td>"
                attrIndex += 1
            elif isinstance(element, float) and 'Qty' not in attr:
                if attr in all_tickers:
                    ret_str += '<td>' + babel.numbers.format_currency(element, "USD", locale="en_US") + "</td>"
                else:
                    ret_str += '<td class="text-success">' if element > 0 else '<td class="text-danger">'
                    ret_str += babel.numbers.format_currency(element, "USD", locale="en_US") + "</td>"
            elif element == True:
                ret_str += "<td class='table-success'>" + str(element) + "</td>"
            elif element == False and 'Qty' not in attr:
                ret_str += "<td class='table-danger'>" + str(element) + "</td>"
            else:
                ret_str += "<td>" + str(element) + "</td>"
        ret_str += "</tr>"
    ret_str += "</table>"
    return ret_str

# html codes of tables containing different sets of data, including header, result, and tables
html_content_str = "<html>\n<head>"
html_content_str += '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-Zenh87qX5JnK2Jl0vWa8Ck2rdkQ2Bzep5IDxbcnCeuOxjzrPF/et3URy9Bv1WTRi" crossorigin="anonymous">'
html_content_str += '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/js/bootstrap.bundle.min.js" integrity="sha384-OERcA2EqjJCMA+/3y+gxIOqMEjwtxJY7qPCqsdltbNJuaOe923+mo//f6V8Qbsw3" crossorigin="anonymous"></script>'
html_content_str += "<title>Accelerating Dual Momentum Investing</title>" + \
                   "</head>\n<body><center><font size=6><b>Accelerating Dual Momentum " + \
                   "Investing</b></font></center><br>\n<font size=4><b>" + message_text + \
                   "</b></font><br><br>" + gen_data_str(data, 1 ) + \
                   "<br><b>Buy Signals:</b>" + gen_data_str(buy_signals, 2) + \
                   "<br><b>Results:</b>" + gen_data_str(results, 3) + "</body>\n</html>"
# run the web app using Flask
application = Flask(__name__)
application.add_url_rule('/', 'index', (lambda: html_content_str))
if __name__ == "__main__":
    application.debug = True
    application.run()
