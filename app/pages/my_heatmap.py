import streamlit as st
import pandas as pd
import sys
import os
from streamlit_folium import st_folium

# Add the project root to the system path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if project_root not in sys.path:
	sys.path.append(project_root)

from backend import *

st.set_page_config(layout='wide')


def main():

	#Fetch access token
	access_token = st.session_state['access_token']

	# Fetch activity ids
	activities = get_strava_activities(access_token)
	df = pd.DataFrame(activities)
	activity_ids = df.id[:50]


	# Fetch streams
	keys = 'latlng'
	streams = get_multiple_streams(access_token, activity_ids, keys)
	heatmap = plot_heatmap(streams)
	st_folium(heatmap, width=900, height=700)

if __name__ == '__main__':
	main()