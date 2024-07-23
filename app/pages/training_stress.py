import streamlit as st
import pandas as pd
import sys
import os

# Add the project root to the system path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if project_root not in sys.path:
	sys.path.append(project_root)

from backend import *

def main():

	st.set_page_config(layout="wide")

	if 'access_token' in st.session_state:

		# Title and definitions
		st.header("Your Training Stress Over Time", divider=True)
		st.write("<span style='color: lightblue;'>***Training Stress Score:***</span>  The TSS provides a measure of how hard a workout was, combining both how long you worked out and how hard you worked out. A TSS of 100 is equivalent to riding for one hour at your FTP. If you have a higher TSS, it indicates a more demanding workout, whether due to higher intensity, longer duration, or a combination of both.", unsafe_allow_html=True)
		st.write("<span style='color: lightblue;'>***Chronic Training Load:***</span>  CTL represents the athlete's long-term training load and is calculated over a period of 42 days. Higher CTL indicates a greater ability to handle training stress and higher fitness levels.", unsafe_allow_html=True)
		st.write("<span style='color: lightblue;'>***Acute Training Load:***</span>  ATL represents the athlete's short-term training load and is calculated over a period of 7 days. Higher ATL indicates greater recent training load and higher short-term fatigue.", unsafe_allow_html=True)
		st.write("<span style='color: lightblue;'>***Training Stress Balance:***</span>  TSB is calculated by subtracting ATL from CTL. In general, a positive TSB indicates a more rested state and potential readiness to perform and a negative TSB suggests a more fatigued state. It is necessary to spend periods of time in a fatigued state in order to induce the desired adaptations and improve performance over time. Use the shaded areas in the chart below to guide your training load.", unsafe_allow_html=True)

		# Subtitle
		st.subheader("Chart", divider=True)

		sum_cols = ['distance', 'moving_time', 'total_elevation_gain', 'kilojoules', 'suffer_score', 'tss']
		mean_cols = ['average_watts', 'weighted_average_watts', 'average_cadence', 'average_heartrate', 'max_heartrate', 'average_speed', 'max_speed']
		load_cols = ['chronic_training_load', 'acute_training_load', 'training_stress_balance']

		# Fetch and transform data
		access_token = st.session_state['access_token']
		activities = get_strava_activities(access_token)
		df = format_dataframe(pd.DataFrame(activities))
		df['ftp'] = df['date'].apply(lambda x: get_ftp(x))
		df = ftp_if_tss(df)

		# Resample data for daily plot
		daily_mean = resample_activities(df, mean_cols, 'mean', 'D')
		daily_sum = resample_activities(df, sum_cols, 'sum', 'D')
		daily_sum_with_load = ctl_atl_tsb(daily_sum).fillna(0)
		daily = pd.concat([daily_sum_with_load, daily_mean], axis=1)
		daily = daily[daily.index >= '2022-01-01']

		# Resample data for weekly plot
		weekly_mean = resample_activities(df, mean_cols, 'mean', 'W')
		weekly_sum = resample_activities(df, sum_cols, 'sum', 'W')
		daily_load = daily[load_cols]
		weekly_load = resample_activities(daily_load, load_cols, 'mean', 'W')
		weekly = pd.concat([weekly_sum, weekly_load, weekly_mean], axis=1)
		weekly = weekly[weekly.index >= '2022-01-01']

		# Plot charts
		frequency = st.radio('Frequency', ['Daily', 'Weekly'])

		if frequency == 'Daily':
			st.plotly_chart(training_load_plot(daily))
		else:
			st.plotly_chart(training_load_plot(weekly))

	else:
		auth_url = get_strava_auth_url(CLIENT_ID, REDIRECT_URI)
		st.write("Please authenticate with Strava to proceed. Click the button below.")
		st.link_button("Authenticate with Strava", auth_url)

	


if __name__ == '__main__':
	main()