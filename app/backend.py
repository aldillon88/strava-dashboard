import streamlit as st

import requests
from requests_oauthlib import OAuth2Session
from IPython.display import display, HTML
import urllib3
import os
import json

from notebooks.config import *

import pandas as pd
from datetime import datetime
import time

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium

from urllib.parse import urlencode, urlparse, parse_qs # Delete later


# Disable SSL verification warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Allow OAuth over HTTP for local testing (NOT recommended for production)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Strava API endpoints
AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"

# Your app's Strava API details
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8501'  # This can be any valid URL for local testing

# Scope for the API access
SCOPE = ["activity:read_all"]

# Function to generate the Strava authorization URL
def get_strava_auth_url(client_id, redirect_uri):
	params = {
		'client_id': client_id,
		'response_type': 'code',
		'redirect_uri': redirect_uri,
		'scope': 'read,activity:read_all,profile:read_all',
		'approval_prompt': 'force'
	}
	url = f"https://www.strava.com/oauth/authorize?{urlencode(params)}"
	return url


@st.cache_data
def get_strava_activities(access_token):
	activities = []
	page = 1
	while True:
		url = f"https://www.strava.com/api/v3/athlete/activities"
		headers = {'Authorization': f'Bearer {access_token}'}
		params = {'per_page': 200, 'page': page}
		response = requests.get(url, headers=headers, params=params)
		
		if response.status_code != 200:
			print("Failed to retrieve activities:", response.content)
			break
		
		data = response.json()
		
		if not data:
			break
		
		activities.extend(data)
		page += 1
	
	return activities



@st.cache_data
def get_athlete_info(access_token):
	max_retries = 5  # Number of retries for rate limiting
	retry_delay = 10  # Delay in seconds between retries

	url = f"https://www.strava.com/api/v3/athlete"
	headers = {'Authorization': f'Bearer {access_token}'}

	while True:
		response = requests.get(url, headers=headers)

		if response.status_code == 429:  # Rate limit exceeded
			print("Rate limit exceeded. Retrying...")
			max_retries -= 1
			if max_retries == 0:
				print("Max retries reached. Exiting.")
				break
			time.sleep(retry_delay)
			continue
		
		if response.status_code != 200:
			print("Failed to retrieve profile:", response.content)
			break

		data = response.json()

		if not data:
			break

		keys = ['id', 'firstname', 'lastname', 'city', 'ftp', 'created_at', 'profile']
		filtered_data = {k: v for k, v in data.items() if k in keys}

		return filtered_data


@st.cache_data
def get_athlete_stats(access_token, athlete_id):
	max_retries = 5  # Number of retries for rate limiting
	retry_delay = 10  # Delay in seconds between retries

	url = f"https://www.strava.com/api/v3/athletes/{athlete_id}/stats"
	headers = {'Authorization': f'Bearer {access_token}'}

	while True:
		response = requests.get(url, headers=headers)

		if response.status_code == 429:  # Rate limit exceeded
			print("Rate limit exceeded. Retrying...")
			max_retries -= 1
			if max_retries == 0:
				print("Max retries reached. Exiting.")
				break
			time.sleep(retry_delay)
			continue
		
		if response.status_code != 200:
			print("Failed to retrieve stats:", response.content)
			break

		data = response.json()

		if not data:
			break

		keys = ['ytd_ride_totals', 'ytd_run_totals', 'ytd_swim_totals']
		filtered_data = {key: value for key, value in data.items() if key in keys}
		
		new_cols = {
			'ytd_ride_totals': 'Ride',
			'ytd_run_totals': 'Run',
			'ytd_swim_totals': 'Swim'
			}

		filtered_data = {new_cols.get(key, key): value for key, value in filtered_data.items()}

		filtered_data = pd.DataFrame(filtered_data)
		filtered_data.loc['distance'] = round(filtered_data.loc['distance'] / 1000, 2)
		filtered_data.loc['moving_time'] = round(filtered_data.loc['moving_time'] / 3600, 2)

		new_index = {
			'count': 'Total Count',
			'distance': 'Total Distance (km)',
			'moving_time': 'Total Moving Time (hours)',
			'elevation_gain': 'Total Elevation Gain (m)'
		}
		
		filtered_data = filtered_data.rename(index=new_index)
		filtered_data.drop('elapsed_time', inplace=True)

		return filtered_data


@st.cache_data
def get_strava_streams(access_token, activity_id, keys):
	max_retries = 5  # Number of retries for rate limiting
	retry_delay = 60  # Delay in seconds between retries

	url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
	headers = {'Authorization': f'Bearer {access_token}'}
	params = {
		'keys': keys,
		'key_by_type': 'true'
	}

	while True:
		response = requests.get(url, headers=headers, params=params)

		if response.status_code == 429:  # Rate limit exceeded
			print("Rate limit exceeded. Retrying...")
			max_retries -= 1
			if max_retries == 0:
				print("Max retries reached. Exiting.")
				break
			time.sleep(retry_delay)
			continue
		
		if response.status_code != 200:
			print("Failed to retrieve activities:", response.content)
			break

		data = response.json()

		if not data:
			break

		if keys not in data:
			print(f"{keys} stream not available.")
			return None

		return data[keys]['data']


@st.cache_data
def get_multiple_streams(access_token, activity_ids, keys):
	streams = []
	for activity_id in activity_ids:
		stream = get_strava_streams(access_token, activity_id, keys)#[keys]['data']
		streams.append(stream)

	return streams


@st.cache_resource
def plot_heatmap(coordinates_list):
	tiles = 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png'
	attr = '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
	m = folium.Map(location=(52.5740, 13.4101), tiles=tiles, attr=attr)
	for coordinates in coordinates_list:
		if coordinates != None:
			folium.PolyLine(coordinates, color='#EB33FF', weight=2, opacity=0.6).add_to(m)
	
	return m


def format_dataframe(df):
	df = df.copy()

	# Format distance, speed and duration measurements.
	df.distance = df.distance / 1000
	df.average_speed = df.average_speed * 3600 / 1000
	df.max_speed = df.max_speed * 3600 / 1000
	df.moving_time = df.moving_time / 3600
	df.elapsed_time = df.elapsed_time / 3600

	# Format date / time columns.
	df['date'] = pd.to_datetime(df['start_date_local']).dt.strftime('%Y-%m-%d')
	
	return df

def get_ftp(date):
	ftp_changes = {
		'2021-10-25': 211,
		'2022-01-30': 237,
		'2022-12-17': 249,
		'2023-03-25': 265,
		'2023-10-05': 256,
		'2023-11-22': 262,
		'2024-02-14': 266,
		'2024-03-13': 272,
		'2024-04-15': 277,
		'2024-06-27': 279,
	}
	
	if isinstance(date, str):
		date = datetime.strptime(date, '%Y-%m-%d')
	elif isinstance(date, pd.Timestamp):
		date = date.to_pydatetime()
	
	sorted_dates = sorted(ftp_changes.keys())
	
	for i, change_date in enumerate(sorted_dates):
		change_date = datetime.strptime(change_date, '%Y-%m-%d')
		
		if date < change_date:
			if i == 0:
				return ftp_changes[sorted_dates[0]]
			return ftp_changes[sorted_dates[i-1]]
		
		if i == len(sorted_dates) - 1 or date < datetime.strptime(sorted_dates[i+1], '%Y-%m-%d'):
			return ftp_changes[sorted_dates[i]]
	
	return None  # This should never be reached if the input is valid


def ftp_if_tss(df):
	df = df.copy()
	df['ftp'] = df['date'].apply(get_ftp)
	df['intensity_factor'] = df.weighted_average_watts / df.ftp
	df['tss'] = (((df.moving_time * 3600) * df.weighted_average_watts * df.intensity_factor) / (df.ftp * 3600)) * 100
	return df


def resample_activities(df, cols_to_resample, agg='sum', period='D'):
	df = df.copy()
	
	existing_cols = df.columns
	cols = []

	for col in existing_cols:
		if col in cols_to_resample:
			cols.append(col)
	
	df = df.groupby(by='date')[cols].agg(agg).sort_index()
	df.index = pd.to_datetime(df.index)
	df = df.resample(period).agg(agg).fillna(0) # For weekly resampling this uses the label='right' argument by default
	return df


def ctl_atl_tsb(df):
	df = df.copy()
	df['chronic_training_load'] = df.tss.rolling(window=42).sum() / 42
	df['acute_training_load'] = df.tss.rolling(window=7).sum() / 7
	df['training_stress_balance'] = df.chronic_training_load - df.acute_training_load
	return df


def training_load_plot(df):
	# Create a subplot figure with 2 rows, 1 column, shared x-axes, and custom titles
	fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
						row_heights=[0.3, 0.3, 0.4])

	# Create traces for each data series
	traces = [
		go.Bar(x=df.index, y=df['tss'], name='Training Stress Score', visible=True),
		go.Scatter(x=df.index, y=df['chronic_training_load'], name='Chronic Training Load', visible=True),
		go.Scatter(x=df.index, y=df['acute_training_load'], name='Acute Training Load', visible=True),
		go.Scatter(x=df.index, y=df['training_stress_balance'], name='Training Stress Balance', visible=True, line=dict(color='white'))
	]
	
	# Add traces to the appropriate subplots
	fig.add_trace(traces[0], row=1, col=1)  # TSS bar chart
	fig.add_trace(traces[1], row=2, col=1)  # Chronic Training Load line
	fig.add_trace(traces[2], row=2, col=1)  # Acute Training Load line
	fig.add_trace(traces[3], row=3, col=1)  # Training Stress Balance line
	
	# Update the layout of the figure
	fig.update_layout(
		xaxis3=dict(  # Configure the x-axis for the second subplot
			rangeselector=dict(  # Add buttons for quick date range selection
				buttons=list([
					dict(count=1, label="1m", step="month", stepmode="backward"),
					dict(count=6, label="6m", step="month", stepmode="backward"),
					dict(count=1, label="YTD", step="year", stepmode="todate"),
					dict(count=1, label="1y", step="year", stepmode="backward"),
					dict(step="all")
				]),
				x=0.0, y=-0.2, xanchor='left', yanchor='top'
			),
			rangeslider=dict(visible=True, thickness=0.05),  # Hide the range slider
			type="date"  # Set the axis type to date
		),
		autosize=False,  # Disable auto-sizing
		height=800,  # Set the height of the figure
		width=1100,  # Set the width of the figure
		margin=dict(t=10, b=40, l=10, r=10)
	)

	
	fig.add_hrect(y0=5, y1=20, row=3, col=1, exclude_empty_subplots=True, annotation=None, line_width=0, fillcolor="blue", opacity=0.5, layer='below') # Fresh
	fig.add_hrect(y0=-10, y1=5, row=3, col=1, exclude_empty_subplots=True, annotation=None, line_width=0, fillcolor="white", opacity=0.5, layer='below') # Grey zone    
	fig.add_hrect(y0=-10, y1=-30, row=3, col=1, exclude_empty_subplots=True, annotation=None, line_width=0, fillcolor="green", opacity=0.5, layer='below') # Optimal
	fig.add_hrect(y0=-100, y1=-30, row=3, col=1, exclude_empty_subplots=True, annotation=None, line_width=0, fillcolor="red", opacity=0.5, layer='below') # High risk
	
	# Return the figure
	return fig


def make_metrics_plot(df):
	fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.05,
							row_heights=[0.2, 0.2, 0.2, 0.2, 0.2])
	
	traces = [
		go.Scatter(x=monthly.index, y=monthly.average_watts, name='Average Power', visible=True),
		go.Scatter(x=monthly.index, y=monthly.weighted_average_watts, name='Weighted Average Power', visible=True),
		go.Scatter(x=monthly.index, y=monthly.average_cadence, name='Average Cadence'),
		go.Scatter(x=monthly.index, y=monthly.average_speed, name='Average Speed'),
		go.Scatter(x=monthly.index, y=monthly.average_heartrate, name='Average Heartrate'),
		go.Scatter(x=monthly.index, y=monthly.max_heartrate, name='Average Max. Heartrate')
	]
	
	fig.add_trace(traces[0], row=1, col=1)
	fig.add_trace(traces[1], row=1, col=1)
	fig.add_trace(traces[2], row=2, col=1)
	fig.add_trace(traces[3], row=3, col=1)
	fig.add_trace(traces[4], row=4, col=1)
	fig.add_trace(traces[5], row=5, col=1)
	
	fig.update_layout(
			xaxis5=dict(  # Configure the x-axis for the second subplot
				rangeselector=dict(  # Add buttons for quick date range selection
					buttons=list([
						dict(count=1, label="1m", step="month", stepmode="backward"),
						dict(count=6, label="6m", step="month", stepmode="backward"),
						dict(count=1, label="YTD", step="year", stepmode="todate"),
						dict(count=1, label="1y", step="year", stepmode="backward"),
						dict(step="all")
					]),
					x=0.0, y=-0.2, xanchor='left', yanchor='top'
				),
				rangeslider=dict(visible=True, thickness=0.05),  # Hide the range slider
				type="date"  # Set the axis type to date
			),
			autosize=False,  # Disable auto-sizing
			height=800,  # Set the height of the figure
			width=1100  # Set the width of the figure
		)
	
	return fig
