import streamlit as st
import sys
import os
import pandas as pd

# Add the project root to the system path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if project_root not in sys.path:
	sys.path.append(project_root)

from backend import *


def main():

	st.set_page_config(layout="wide")

	st.title('Welcome to your Strava Dashboard')

	# First check if the user has authorized the app to connect to Strava
	if 'code' in st.query_params:

		# Add a session state indicating that the session is authorized by Strava and add authorization code to session state
		st.session_state['authorized'] = True
		st.session_state['auth_code'] = st.query_params['code']
	
		#if 'auth_code' in st.session_state:
		auth_code = st.session_state['auth_code']
		token_url = 'https://www.strava.com/oauth/token'
		payload = {
			'client_id': CLIENT_ID,
			'client_secret': CLIENT_SECRET,
			'code': auth_code,
			'grant_type': 'authorization_code'
		}
		response = requests.post(token_url, data=payload)
		
		if response.status_code == 200:
			token_info = response.json()
			st.session_state['access_token'] = token_info['access_token']
			st.session_state['athlete_id'] = token_info['athlete']['id']
			access_token = st.session_state['access_token']
			athlete_id = st.session_state['athlete_id']
			athlete = get_athlete_info(access_token)
			athlete_name = athlete['firstname'] + ' ' + athlete['lastname']
			first_seen = pd.to_datetime(athlete['created_at']).date()
			st.divider()
			st.image(athlete['profile'])
			st.write(f"**Athlete:**  {athlete_name}  \n**Member since:**  {first_seen}")
			stats = get_athlete_stats(access_token, athlete_id)
			if stats is not None:
				st.subheader('Your stats so far this year...', divider=True)
				stats = stats.style.format(precision=0)
				st.dataframe(stats, use_container_width=True)
		
		else:
			st.write("Failed to get access token. Please try again.")
			st.write(response)
			st.write(response.content)


	# Check if this is a new session
	if 'code' not in st.query_params:

		# Initiate the OAuth process
		if 'authorized' not in st.session_state:
			auth_url = get_strava_auth_url(CLIENT_ID, REDIRECT_URI)
			st.write("## Step 1: Authenticate with Strava")
			st.write("Click the button below to authenticate with Strava.")
			st.link_button("Authenticate with Strava", auth_url)
			#if st.button("Authenticate with Strava"):
			#	st.write("Please follow [this link]({}) to authenticate.".format(auth_url))

		elif st.session_state['authorized'] == True:
			access_token = st.session_state['access_token']
			athlete_id = st.session_state['athlete_id']
			athlete = get_athlete_info(access_token)
			athlete_name = athlete['firstname'] + ' ' + athlete['lastname']
			first_seen = pd.to_datetime(athlete['created_at']).date()
			st.subheader("Athlete profile", divider=True)
			st.image(athlete['profile'])
			st.write(f"**Athlete:**  {athlete_name}  \n**Member since:**  {first_seen}")
			stats = get_athlete_stats(access_token, athlete_id)
			if stats is not None:
				st.subheader('Your stats so far this year...', divider=True)
				stats = stats.style.format(precision=0)
				st.dataframe(stats, use_container_width=True)


		else:
			st.write('this session has not been authorized')
			st.link_button("Authenticate with Strava", auth_url)



if __name__ == '__main__':
	main()
