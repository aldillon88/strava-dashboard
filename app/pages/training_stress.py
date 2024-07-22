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

	


if __name__ == '__main__':
	main()