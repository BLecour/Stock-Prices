import config
import discord
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name="type !help"))
    print("Logged in as {0.user}".format(client))

@client.event
async def on_message(message):

    async def printPrice(stockName):
        
        # load the info about the given stock
        stock = yf.Ticker(stockName)
        negativeFlag = False

        # make sure the stock exists
        try:
            # get the current price from the stock info
            price = stock.info["currentPrice"]
        except (IndexError, KeyError):
            # give error if the stock doesn't exist
            await message.channel.send(":no_entry_sign: An error has occured. This stock ticker does not exist. Check the spelling of the stock ticker and try again.")

        # always have 2 decimals in price, ex. $1.1 to $1.10
        if list(str(price)).count('.') == 0 or len(str(price).split('.', 1)[1]) < 2:
            price = format(price, ".2f")
        
        # calculate the price difference from yesterday
        yesterdaysPrice = stock.info["previousClose"]
        priceChange = float(price) - yesterdaysPrice
        
        if priceChange < 0:
            priceChange *= -1
            negativeFlag = True

        priceChangePercent = round(priceChange / yesterdaysPrice * 100, 2)

        # is price is < $1, use 4 decimal places for the price change
        if float(price) < 1:
            if priceChange < 0:
                negativeFlag = True
            priceChange = format(priceChange, ".4f")
        else:
            priceChange = round(priceChange, 2)
        
        # send a different message based on the sign of the price change (positive/negative)
        if negativeFlag:
            await message.channel.send(f"${stockName.upper()} = ${price} \n-${priceChange} :chart_with_downwards_trend: \n{priceChangePercent*-1}%")
        else:
            await message.channel.send(f"${stockName.upper()} = ${price} \n+${priceChange} :chart_with_upwards_trend: \n+{priceChangePercent}%")      

    # ignore any message sent by the bot
    if message.author == client.user:
        return

    if message.content.startswith("!help"):

        # send a message with all the commands for the bot
        await message.channel.send("\
        :money_with_wings: Get stock price: !get {stock symbol}\n"
        ":date: Get stock price on specific date: !get {stock symbol} {date: YYYY-MM-DD}\n"
        ":scissors: Get most recent stock split: !split {stock symbol}\n"
        ":thinking: Get recommendation rating: !rec {stock symbol}\n"
        ":chart_with_upwards_trend: Get stock price of today's biggest gainer: !topgainer\n"
        ":chart_with_downwards_trend: Get stock price of today's biggest loser: !toploser\n"
        ":bar_chart: Get stock's range for today: !range {stock symbol}")

    if message.content.startswith("!get"):

        stockName = str(message.content.split(" ")[1])
        stock = yf.Ticker(stockName)

        # if there are only 2 parts to the message ("!get" and the stock name, "AAPL" for ex.)
        if len(message.content.split(' ')) == 2:
            await printPrice(stockName)

        # if the user specified a date, then execute this part
        else: 
            # this will calculate the range
            date = str(message.content.split(' ')[2])
            dates = date.split('-')

            if len(dates) != 3:
                await message.channel.send(":no_entry_sign: An error has occured. If you would like to get the stock price on a specific date, the syntax is: !get {stock symbol} {date: YYYY-MM-DD}")
                return
            
            # get the stock history info on that date
            endDate = int(dates[2]) + 1
            if endDate < 10:
                endDates = dates[0] + '-' + dates[1] + '-' + '0' + str(endDate)
            else:
                endDates = dates[0] + '-' + dates[1] + '-' + str(endDate)
            historyDF = stock.history(start=date, end=endDates, interval="1d", actions=False)

            # check to see if data was returned for the specified date
            if historyDF.empty:
                await message.channel.send(":no_entry_sign: An error has occured. Ensure that the selected date is a business day and try again.")

            else:
                historicalPrice = float(historyDF.iloc[0]["Close"])

                # if price is lower than $1, round to 4 decimals
                if historicalPrice < 1:
                    historicalPrice = format(historicalPrice, ".4f")

                # if price is greater than or equal to $1, round to 2 decimals
                else:
                    historicalPrice = format(historicalPrice, ".2f")

                # print the current price along with the historical price
                currentPrice = format(stock.info["currentPrice"])
                percentChange = round((float(currentPrice) - float(historicalPrice)) / float(historicalPrice) * 100, 2)
                if float(currentPrice) >= float(historicalPrice):
                    await message.channel.send(f"The price of ${stockName.upper()} on {date} was ${historicalPrice}. Today, ${stockName.upper()} is worth ${currentPrice}, a {percentChange}% increase :chart_with_upwards_trend:")
                else:
                    percentChange *= -1
                    await message.channel.send(f"The price of ${stockName.upper()} on {date} was ${historicalPrice}. Today, ${stockName.upper()} is worth ${currentPrice}, a {percentChange}% decrease :chart_with_downwards_trend:")

    # get any stock split information
    if message.content.startswith("!split"):

        # get the ticker info
        stockName = str(message.content.split(" ")[1])
        stock = yf.Ticker(stockName)
        
        # if the stock does not exist, give an error
        try:
            # try to access ticker info, it will throw an error if the stock does not exist
            price = stock.info["currentPrice"]
        except (IndexError, KeyError):
            # give error if the stock doesn't exist
            await message.channel.send(":no_entry_sign: An error has occured. This stock ticker does not exist. Check the spelling of the stock ticker and try again.")
            return
        
        # get all info about splits from the ticker
        splitsDF = stock.splits

        if splitsDF.empty:
            # give message if no splits have ever occured
            await message.channel.send(f":no_entry_sign: ${stockName.upper()} has never had a stock split.")
        else:

            # change message depending on number of splits
            if len(splitsDF == 1):          
                messageString = f"${stockName.upper()} has had 1 stock split:\n"
            else: 
                messageString = f"${stockName.upper()} has had {len(splitsDF)} stock splits:\n"

            # loop for each stock split that the stock has had
            for i in range(len(splitsDF)):

                # get date from pandas dataframe
                date = str(splitsDF.index[i]).split(' ', 1)[0]

                # change message depending on if it was a reverse split
                split = float(splitsDF[i])
                if split < 1:
                    split = 1 / split
                    messageString += f"{date}: 1 to {split}.\n"
                else:
                    messageString += f"{date}: {split} to 1.\n"

            # send the entire message at once
            await message.channel.send(messageString)

    # get a stock's recommendation status
    if message.content.startswith("!rec"):

        # get the stock ticker and information
        stockName = str(message.content.split(" ")[1])
        stock = yf.Ticker(stockName)

        # get the current recommendation status for the ticker
        try:
            # try to access ticker info, it will throw an error if the stock does not exist
            recommendation = stock.info["currentPrice"]
        except (IndexError, KeyError):
            # give error if the stock doesn't exist
            await message.channel.send(":no_entry_sign: An error has occured. This stock ticker does not exist. Check the spelling of the stock ticker and try again.")
            return

        # print a different message depending on the recommendation status
        if recommendation == "strong buy":
            await message.channel.send(f":moneybag: ${stockName.upper()}'s recommendation rating is Strong Buy.")
        elif recommendation == "buy":
            await message.channel.send(f":dollar: ${stockName.upper()}'s recommendation rating is Buy.")
        elif recommendation == "hold":
            await message.channel.send(f":raised_hand: ${stockName.upper()}'s recommendation rating is Hold.")
        elif recommendation == "underperform":
            await message.channel.send(f":chart_with_downwards_trend: ${stockName.upper()}'s recommendation rating is Underperforming.")
        elif recommendation == "sell":
            await message.channel.send(f":x: ${stockName.upper()}'s recommendation rating is Sell.")
        else:
            await message.channel.send(f":question: ${stockName.upper()} does not have a recommendation rating!")

    if message.content.startswith("!topgainer"):
        soup = BeautifulSoup(requests.get("https://finance.yahoo.com/gainers").text, 'html.parser')
        topGainer = str(soup.find_all('a', attrs={"class":"Fw(600)"}))
        # remove unnecessary text to locate the #1 top gainer
        topGainer = topGainer.split('"quoteLink" href="/quote/', 1)[1]
        topGainer = topGainer.split("?", 1)[0]
        await printPrice(topGainer)

    if message.content.startswith("!toploser"):
        soup = BeautifulSoup(requests.get("https://finance.yahoo.com/losers").text, 'html.parser')
        topLoser = str(soup.find_all('a', attrs={"class":"Fw(600)"}))
        # remove unnecessary text to locate the #1 top loser
        topLoser = topLoser.split('"quoteLink" href="/quote/', 1)[1]
        topLoser = topLoser.split("?", 1)[0]
        await printPrice(topLoser)

    if message.content.startswith("!range"):
        stockName = str(message.content.split(" ")[1])
        stock = yf.Ticker(stockName)
        low = stock.info["regularMarketDayLow"]
        high = stock.info["regularMarketDayHigh"]
        await message.channel.send(f":bar_chart: ${stockName.upper()}'s range: ${low} - ${high}")

client.run(config.BOT_TOKEN)