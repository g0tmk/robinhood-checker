import csv
import logging


class TickerNotFoundError(Exception):
	pass


class CategoryNotFoundError(Exception):
	pass


class ParseError(Exception):
	pass


class Category():
	def __init__(self, name, allocation_percentage):
		self.name = name
		self.tickers = []
		try:
			self.allocation_percentage = float(allocation_percentage.replace('%', ''))
		except TypeError:
			raise ParseError(f"Allocation must be a percentage between 0 and "
							 f"100 (found {repr(allocation_percentage)})")


class Ticker():
	def __init__(self, name, categories):
		self.name = name
		self.categories = categories


def trim_trailing_empty_values(input_list):
	num_elements = len(input_list)
	if num_elements == 0:
		return input_list

	while num_elements > 0 and input_list[num_elements-1] == "":
		num_elements -= 1

	return input_list[:num_elements]


class StockCategories():
	def __init__(self, categories_csv_file):
		self._categories_csv_file = categories_csv_file
		self.csv_data = None


	def load_info_from_csv(self):
		if not self.csv_data:
			self.csv_data = self._load_info_from_csv()
		return self.csv_data


	def _load_info_from_csv(self):
		reader = csv.reader(self._categories_csv_file)
		categories = []
		categories_by_name = {}
		#tickers = {}
		tickers_by_name = {}
		minimum_cash_amount = None

		# load all basic settings
		while True:
			try:
				row = trim_trailing_empty_values(reader.__next__())
			except StopIteration:
				break

			if len(row) == 0:
				continue
			elif row[0] == "Category":
				break
			elif row[0] == "Stock ticker":
				break
			elif row[0] == "Reserved cash amount":
				try:
					minimum_cash_amount = float(row[1])
				except TypeError:
					raise ParseError(f"Invalid value for 'Reserved cash amount': {repr(row[1])}")
			else:
				logging.warning(f"Unrecognized config line {repr(row)}")

		# load all categories
		while True:
			try:
				row = trim_trailing_empty_values(reader.__next__())
			except StopIteration:
				break

			if len(row) == 0:
				continue
			elif row[0] == "Category":
				continue
			elif row[0] == "Stock ticker":
				break
			else:
				category_name, allocation_percentage = row[0], row[1]
				c = Category(category_name, allocation_percentage)
				categories.append(c)
				categories_by_name[category_name] = c

		# load all stock tickers and their categories
		while True:
			try:
				row = trim_trailing_empty_values(reader.__next__())
			except StopIteration:
				break

			if len(row) == 0:
				continue
			elif row[0] == "Stock ticker":
				continue
			else:
				ticker_name, category_names = row[0], row[1:]
				t = Ticker(ticker_name, category_names)
				tickers_by_name[ticker_name] = t
				for category_name in category_names:
					categories_by_name[category_name].tickers.append(t)

		if minimum_cash_amount is None:
			raise ParseError("Missing required setting 'Reserved cash amount'")

		return minimum_cash_amount, categories_by_name, tickers_by_name


	def get_categories_of_stock_ticker(self, stock_ticker):
		minimum_cash_amount, categories_by_name, tickers_by_name = self.load_info_from_csv()
		try:
			return tickers_by_name[stock_ticker].categories
		except KeyError:
			raise TickerNotFoundError(f"Failed to find categories for ticker {stock_ticker}")


	def get_categories(self):
		minimum_cash_amount, categories_by_name, tickers_by_name = self.load_info_from_csv()
		categories = []
		for category_name in categories_by_name.keys():
			categories.append(categories_by_name[category_name])
		return categories


	def get_minimum_cash_amount(self):
		minimum_cash_amount, categories_by_name, tickers_by_name = self.load_info_from_csv()
		return minimum_cash_amount


	def get_tickers_in_category(self, category_name):
		minimum_cash_amount, categories_by_name, tickers_by_name = self.load_info_from_csv()
		try:
			category = categories_by_name[category_name]
		except KeyError:
			raise CategoryNotFoundError(f"Failed to find category {category}")
		else:
			return category.tickers


if __name__ == "__main__":
	c = StockCategories('stock_categories.csv')
	minimum_cash_amount, categories_by_name, tickers_by_name = c.load_info_from_csv()
	print(c.get_categories_of_stock_ticker('SPY'))


