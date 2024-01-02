import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime

# define functions
def style_negative(v, props=''):
    try:
        return props if v < 0 else None
    except:
        pass


def style_positive(v, props=''):
    try:
        return props if v > 0 else None
    except:
        pass

def audience_simple(country):
    if country == 'US':
        return 'USA'
    elif country == 'IN':
        return 'India'
    else:
        return 'Other'


# load data
@st.cache_data
def load_data():
    """return data : (df_agg, df_agg_sub, df_comments, df_time)"""
    df_agg = pd.read_csv('data/archive/Aggregated_Metrics_by_Video.csv') #, parse_dates=['Video publish time'])
    
    df_agg['Video publish time'] = pd.to_datetime(df_agg['Video publish time'], format="mixed")
    df_agg['Avg_duration_sec'] = df_agg['Average view duration'].apply(lambda s: sum(60 ** (2 - p) * v for p, v in enumerate(map(int,s.split(':')))))
    df_agg['Engagement_ratio'] = (df_agg['Comments added'] + df_agg['Shares'] + df_agg['Dislikes'] + df_agg['Likes']) / df_agg.Views
    df_agg['Views / sub gained'] = df_agg['Views'] / df_agg['Subscribers gained']
    df_agg.sort_values("Video publish time", ascending=False, inplace=True)
    df_agg_sub = pd.read_csv('data/archive/Aggregated_Metrics_by_Country_And_Subscriber_Status.csv')
    df_comments = pd.read_csv('data/archive/All_Comments_Final.csv')
    df_time = pd.read_csv('data/archive/Video_Performance_Over_Time.csv')
    df_time['Date'] = pd.to_datetime(df_time['Date'], format='mixed')

    return df_agg, df_agg_sub, df_comments, df_time

df_agg, df_agg_sub, df_comments, df_time = load_data()

# engineer data
df_agg_diff = df_agg.copy()
#print(df_agg_diff.dtypes)
#print(df_agg.dtypes)
metric_date_12mo = df_agg_diff['Video publish time'].max() - pd.DateOffset(months=12)
#print(metric_date_12mo, type(metric_date_12mo))
numeric_cols = np.array((df_agg_diff.dtypes == 'float64') | (df_agg_diff.dtypes == 'int64'))
mix = df_agg_diff['Video publish time'] >= metric_date_12mo
median_agg = df_agg_diff.loc[mix, numeric_cols].median()

df_agg_diff.iloc[:, numeric_cols] = (df_agg_diff.iloc[:, numeric_cols] - median_agg).div(median_agg)

df_time_diff = pd.merge(df_time, df_agg.loc[:, ['Video', 'Video publish time']], left_on='External Video ID', right_on='Video')
df_time_diff['days_published'] = (df_time_diff['Date'] - df_time_diff['Video publish time']).dt.days

date_12mo = df_agg['Video publish time'].max() - pd.DateOffset(months=12)
df_time_diff_yr = df_time_diff[df_time_diff['Video publish time'] >= date_12mo]

# get daily view data (first 30), median & percentiles
views_days = pd.pivot_table(df_time_diff_yr, index='days_published', values='Views', aggfunc=[np.mean, np.median, lambda x: np.percentile(x, 80), lambda x: np.percentile(x, 20)]).reset_index()
views_days.columns=['days_published', 'mean_views', 'median_views', '80pct_views', '20pct_views']
views_days = views_days[views_days['days_published'].between(0, 30)]
views_cumulative = views_days.loc[:, ['days_published', 'median_views', '80pct_views', '20pct_views']]
views_cumulative.loc[:, ['median_views', '80pct_views', '20pct_views']] = views_cumulative.loc[:, ['median_views', '80pct_views', '20pct_views']].cumsum()


# build dashboard

add_sidebar = st.sidebar.selectbox('Aggregate or Individual Video', ('Aggregate Metrics', 'Individual Analysis'))
## Total Picture
if add_sidebar == 'Aggregate Metrics':
    df_agg_metrics = df_agg[['Video publish time', 'Views', 'Likes', 'Subscribers', 'Shares', 'Comments added',
                              'RPM (USD)', 'Average percentage viewed (%)', 'Avg_duration_sec', 'Engagement_ratio', 'Views / sub gained']]
    metric_date_6mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=6)
    metric_medians6mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_6mo].median()
    metric_date_12mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=12)
    metric_medians12mo = df_agg_metrics[(df_agg_metrics['Video publish time'] >= metric_date_12mo)
                                        & (df_agg_metrics['Video publish time'] <= metric_date_6mo)
                                        ].median()
    
    columns = st.columns(5)
    count = 0
    for i in metric_medians6mo.index[1:]:
        with columns[count]:

            delta = (metric_medians6mo[i] - metric_medians12mo[i])/ metric_medians12mo[i]
            st.metric(label=i, value=round(metric_medians6mo[i], 1), delta=f"{delta:.2%}")
        count = (count + 1) % len(columns)
    df_agg_diff['Publish date'] = df_agg_diff['Video publish time'].dt.date
    df_agg_diff_final = df_agg_diff.loc[:, ['Video title', 'Publish date', 'Views', 'Likes', 'Subscribers',
                                             'Shares', 'Comments added', 'Average percentage viewed (%)',
                                             'Avg_duration_sec', 'Engagement_ratio', 'Views / sub gained'
                                            ]]
    
    st.dataframe(df_agg_diff_final.style.applymap(style_negative, props='color:red;')
                                  .applymap(style_positive, props='color:green;'))
elif add_sidebar == 'Individual Analysis':
    st.write('Individual Video Performance')
    videos = tuple(df_agg['Video title'])
    video_select = st.selectbox('Pick a Video', videos)

    agg_filtered = df_agg[df_agg['Video title'] == video_select]
    agg_sub_filtered = df_agg_sub[df_agg_sub['Video Title'] == video_select]
    agg_sub_filtered['Country'] = agg_sub_filtered['Country Code'].apply(audience_simple)
    agg_sub_filtered.sort_values('Is Subscribed', inplace=True)

    fig = px.bar(agg_sub_filtered, x='Views', y='Is Subscribed', color='Country', orientation='h')
    st.plotly_chart(fig)

    agg_time_filtered = df_time_diff[df_time_diff['Video Title'] == video_select]
    first_30 = agg_time_filtered[agg_time_filtered['days_published'].between(0,30)].sort_values('days_published')

    lin = go.Figure()
    lin.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['20pct_views'],
                             mode='lines',
                             name='20th percentile', line={'color': 'purple', 'dash': 'dash'}))
    
    lin.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['median_views'],
                             mode='lines+markers',
                             name='50th percentile', line={'color': 'black'}))
    
    lin.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['80pct_views'],
                             mode='lines',
                             name='80th percentile', line={'color': 'royalblue', 'dash': 'dash'}))
    
    lin.add_trace(go.Scatter(x=first_30['days_published'], y=first_30['Views'].cumsum(),
                             mode='lines',
                             name='80th percentile', line={'color': 'firebrick', 'width': 5}))
    st.plotly_chart(lin)
    