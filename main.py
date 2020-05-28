import Robinhood
import stock_categories
import logging
import argparse
import getpass
import time

_START_TIMESTAMP = time.strftime("%y%m%d_%H%M%S")  # used in filenames

class RobinhoodManager():
	def __init__(self, username, password):
		self._trader = Robinhood.Robinhood()
		self._cached_portfolio_dictionary = None
		self._cached_positions_dictionary = None

		try:
			logged_in = self._trader.login(username=username, password=password)
		except Robinhood.exceptions.LoginFailed:
			raise RuntimeError("Login failed, wrong password?")

	def _update_portfolio_dictionary(self):

		portfolio = self._trader.portfolios()
		# Example portfolio dictionary:
		# {'account': 'https://api.robinhood.com/accounts/123456789/',
		#       "Adjusted" values show how much equity you would have had
		#       yesterday, adjusted by any new/pending deposits. This allows
		#       calculating gains/losses between yesterday & today.
		#  'adjusted_equity_previous_close': '1234.5678',
		#  'adjusted_portfolio_equity_previous_close': '1234.5678',
		#  'equity': '1234.5678',
		#  'equity_previous_close': '1234.5678',
		#  'portfolio_equity_previous_close': '1234.5678',
		#  'excess_maintenance': '1234.5678',
		#  'excess_maintenance_with_uncleared_deposits': '1234.5678',
		#  'excess_margin': '1234.5678',
		#  'excess_margin_with_uncleared_deposits': '1234.5678',
		#  'extended_hours_equity': '1234.5678',
		#  'extended_hours_market_value': '1234.5678',
		#  'extended_hours_portfolio_equity': '1234.5678',
		#  'last_core_equity': '1234.5678',
		#  'last_core_market_value': '1234.5678',
		#  'last_core_portfolio_equity': '1234.5678',
		#  'market_value': '1234.5678',
		#  'start_date': '2020-01-01',
		#  'unwithdrawable_deposits': '0.0000',
		#  'unwithdrawable_grants': '0.0000',
		#  'url': 'https://api.robinhood.com/portfolios/123456789/',
		#  'withdrawable_amount': '1234.5678'}

		equity = float(portfolio['equity'])
		equity_previous_close = float(portfolio['adjusted_equity_previous_close'])
		cash_amount = equity - float(portfolio['market_value'])

		result_dict = {
			"equity": equity,
			"equity_previous_close": equity_previous_close,
			"equity_percent_change_today": (equity - equity_previous_close) / equity_previous_close,
			"cash_amount": cash_amount,
			"cash_percentage": float(cash_amount / equity)
		}
		self._cached_portfolio_dictionary = result_dict

	@property
	def portfolio_dictionary(self):
		if self._cached_portfolio_dictionary is None:
			self._update_portfolio_dictionary()

		return self._cached_portfolio_dictionary

	def portfolio_readable_string(self):
		portfolio = self.portfolio_dictionary
		return "${:.2f} {:+.1f}%; ${:.2f} ({:.0f}%) cash".format(
			portfolio["equity"],
			portfolio["equity_percent_change_today"]*100,
			portfolio["cash_amount"],
			portfolio["cash_percentage"]*100,
		)

	def _update_positions_dictionary(self):
		positions = self._trader.positions()['results']		
		number_of_positions = int(len(positions))
		results = {}
		
		for position in positions:
			quantity = float(position['quantity'])
			average_buy_price = float(position["average_buy_price"])

			instrument = self._trader.session.get(position['instrument'], timeout=15).json()
			symbol = instrument["symbol"]
			name = instrument["simple_name"]

			quote = self._trader.quote_data(symbol)
			current_price = float(quote["last_trade_price"])
			previous_close_price = float(quote["previous_close"])
			price_change_percent_today = (current_price - previous_close_price) / previous_close_price

			total_cost = quantity * average_buy_price
			total_value = quantity * current_price
			total_return_amount = total_value - total_cost
			total_return_percent = 0 if total_cost == 0 else total_return_amount / total_cost

			results[symbol] = {
				"symbol": symbol,
				"quantity": quantity,
				"average_buy_price": average_buy_price,
				"current_price": current_price,
				"previous_close_price": previous_close_price,
				"price_change_percent_today": price_change_percent_today*100,
				"total_cost": total_cost,
				"total_value": total_value,
				"total_return_amount": total_return_amount,
				"total_return_percent": total_return_percent*100,
			}

		self._cached_positions_dictionary = results

	@property
	def positions_dictionary(self):
		if self._cached_positions_dictionary is None:
			self._update_positions_dictionary()

		return self._cached_positions_dictionary

	def positions_csv(self):
		output = "{},{},{},{},{},{}\r\n".format(
			"Symbol",
			"Price",
			"Change",
			"Equity",
			"Cost",
			"Return",
		)
		for symbol in self.positions_dictionary:
			entry = self.positions_dictionary[symbol]
			output += "{},{},{},{},{},{}\r\n".format(
				format("{}".format(entry["symbol"])),
				format("${:.3f}".format(entry["current_price"])),
				format("{:.2f}%".format(entry["price_change_percent_today"])),
				format("${:.3f}".format(entry["total_value"])),
				format("${:.3f}".format(entry["total_cost"])),
				format("{:.2f}%".format(entry["total_return_percent"])),
			)
		return output

	def positions_readable_table(self):
		print("{:<7}{:>8}{:>8}{:>8}{:>8}{:>8}".format(
			"Symbol",
			"Price",
			"Change",
			"Equity",
			"Cost",
			"Return",
		))
		for symbol in self.positions_dictionary:
			entry = self.positions_dictionary[symbol]
			print("{:<7}{:>8}{:>8}{:>8}{:>8}{:>8}".format(
				format("{}".format(entry["symbol"])),
				format("${:.2f}".format(entry["current_price"])),
				format("{:+.1f}%".format(entry["price_change_percent_today"])),
				format("${:.2f}".format(entry["total_value"])),
				format("${:.2f}".format(entry["total_cost"])),
				format("{:+.1f}%".format(entry["total_return_percent"])),
			))


def print_section_header(text):
	print()
	print("{:#^66s}".format(' ' + text + ' '))


def main():
	parser = argparse.ArgumentParser(description='Display information for a Robinhood account.')

	parser.add_argument('--categories_file', type=argparse.FileType('r'),
		default='stock_categories.csv', help='location of the stock categories CSV file')
	parser.add_argument('--output_csv_location',
		default='stock_holdings_{}.csv'.format(_START_TIMESTAMP),
		help='location to save current stock data')
	parser.add_argument('--username', help='account username')
	args = parser.parse_args()

	# repeatedly ask for credentials + login until successful
	while True:
		if args.username:
			username = args.username
		else:
			username = input('Robinhood Username: ')

		password = getpass.getpass(prompt='Robinhood Password: ')
		try:
			r = RobinhoodManager(username, password)
		except Exception as e:
			print("Failed to login to Robinhood, try again. (Error:{})".format(e))
		else:
			break

	sc = stock_categories.StockCategories(args.categories_file)


	## Print basic portfolio stats
	print_section_header("Robinhood")
	print(f"Equity: {r.portfolio_readable_string()}")
	print("Reserved cash: ${:.0f} / ${:.0f} ({:.0f}%)".format(
		r.portfolio_dictionary['cash_amount'],
		sc.get_minimum_cash_amount(),
		100.0 * r.portfolio_dictionary['cash_amount'] / sc.get_minimum_cash_amount()))


	## Print portfolio positions in a table
	print_section_header("Positions")
	r.positions_readable_table()
	with open(args.output_csv_location, 'w') as handle:
		print(r.positions_csv(), file=handle)


	## Print categories used to balance portfolio
	print_section_header("Portfolio balance")
	print("{:<30}{:>7}{:>7}{:>7}  {}".format("Category", "Ideal", "Actual", "Needed", "Holdings"))
	for category in sc.get_categories():
		allocation_to_category = 0
		stocks_in_category = sc.get_tickers_in_category(category.name)
		for ticker in stocks_in_category:
			if ticker.name == "Cash":
				allocation_to_category = r.portfolio_dictionary['cash_amount'] - sc.get_minimum_cash_amount()
				if allocation_to_category < 0:
					# if cash allocation is negative (less cash then reserved amount)
					allocation_to_category = 0
			else:
				try:
					position = r.positions_dictionary[ticker.name]
				except KeyError:
					pass  # ticker not in portfolio; skip
				else:
					allocation_to_category += position["total_value"] / len(ticker.categories)

		actual_allocation_percentage = 100.0 * allocation_to_category / r.portfolio_dictionary['equity']
		print("{:<30}{:>7}{:>7}{:>7}  {}".format(
			category.name,
			"{:.1f}%".format(category.allocation_percentage),
			"{:.1f}%".format(actual_allocation_percentage),
			"{:.1f}%".format(category.allocation_percentage - actual_allocation_percentage),
			" ".join([t.name for t in stocks_in_category])))
	print()

	## Print warnings/notifications
	uncategorized_tickers = []
	for ticker_name in r.positions_dictionary:
		try:
			sc.get_categories_of_stock_ticker(ticker_name)
		except stock_categories.TickerNotFoundError:
			uncategorized_tickers.append(ticker_name)
	if len(uncategorized_tickers) > 0:
		print_section_header("Warnings")
		logging.warning(f"Some tickers are not categorized: {', '.join(uncategorized_tickers)}")



if __name__ == "__main__":
	main()