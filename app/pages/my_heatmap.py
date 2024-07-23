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

#st.set_page_config(layout='wide')


def main():

	st.set_page_config(layout="wide")

	if 'access_token' in st.session_state:

		st.header("Your Heatmap", divider=True)

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

	else:
		auth_url = get_strava_auth_url(CLIENT_ID, REDIRECT_URI)
		st.write("Please authenticate with Strava to proceed. Click the button below.")
		st.link_button("Authenticate with Strava", auth_url)

if __name__ == '__main__':
	main()