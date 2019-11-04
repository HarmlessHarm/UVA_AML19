
import numpy as np
import requests


def download_heart_disease_file():
	data_url = "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data"
	try:
		response = requests.get(data_url)
		data = response.text
		return data
	except Exception:
		print("Download did not work, try manually downloading: ", data_url)


def prep_heart_disease_data(data):
	data = data.strip().split('\n')
	filtered_data = []
	for row in data:
		try:
			filtered_data.append([float(v) for v in row.split(',')])
		except Exception:
			continue
	data_arr = np.array(filtered_data)
	X = data_arr[:, :-1]
	Y = (data_arr[:, -1:] > 0.).astype('float')

	return X, Y


def download_and_preprocess():
    data = download_heart_disease_file()
    return prep_heart_disease_data(data)