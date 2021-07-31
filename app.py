import streamlit as st
import pandas as pd

import plotly.express as px
import plotly.graph_objects as go

from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

from datetime import datetime

import requests

st.title("Subreddit Threads Dashboard")

@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def get_data_dataframe():
    df_full_data = pd.read_csv('./Data/tagged_threads.csv')
    df_full_data = df_full_data.sort_values(by=['score'],ascending=False)
    return df_full_data

@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def make_group_by_monthly(df):
    df['created'] = pd.to_datetime(df['created'])
    df['year_month'] = df['created'].dt.strftime('%Y-%m')
    tag_count_monthly = df.groupby(['year_month','tag']).submission_id.count().reset_index()
    return tag_count_monthly

df_full_data = get_data_dataframe()
df_monthly = make_group_by_monthly(df_full_data)

# make API call to reddit

# set up paramters
class competitorMention():
    def __init__(self):
        self.scan_url = "https://api.pushshift.io/reddit/search/submission/?q=goodnotes&subreddit=notabilityapp,evernote,onenote,notion,RoamResearch&after=10d&before=1h&sort=desc&sort_type=score"
        self.submission_raw = None
        self.submission_dict = None
        self.submission_dataframe = None
                 
    def grab_latest_submission(self):
        r = requests.get(self.scan_url)
        result = None
        if r.status_code == 200:
            result = r.json()
        self.submission_raw = result
        
    def get_comments_data(self,submission_id):
        comment_id_list_url = 'https://api.pushshift.io/reddit/submission/comment_ids/{}'.format(submission_id)
        r = requests.get(comment_id_list_url)
        result = None
        comments_result = None
        if r.status_code == 200:
            result = r.json()
            comment_ids = result['data']
            comment_ids_string = ','.join(comment_ids)
            comments_url = 'https://api.pushshift.io/reddit/comment/search?ids={}&&fields=body,author,created_utc,score'.format(comment_ids_string)
            comments_r = requests.get(comments_url)
            if comments_r.status_code == 200:
                comments_result = comments_r.json()['data']
        return comments_result    
        
    def get_comments(self):
        if self.submission_raw:            
            all_submissions = self.submission_raw['data']
            if len(all_submissions) >0:
                for submission in all_submissions:
                    cur_submission_id = submission['id']
                    all_comments = self.get_comments_data(cur_submission_id)
                    submission['comments_list'] = all_comments
            self.submission_dict = all_submissions
        else:
            st.markdown("Did not see any mentions for the past 10 days in comeptitors reddits")

    # caching so that on reload doesn't re-run again
    @st.cache(suppress_st_warning=True)
    def get_submission_dataframe(self)-> pd.DataFrame:
        self.grab_latest_submission()
        self.get_comments()
        result = None
        if len(self.submission_dict) >0:
            df = pd.DataFrame(self.submission_dict)
            result = df
        return result

st.markdown("## **Threads mentioning GoodNote in other competitor subreddits**")
thisListener= competitorMention()
result_df = thisListener.get_submission_dataframe()
result_df = result_df[['subreddit','created_utc','title','selftext','num_comments','full_link']]
result_df['created_utc'] = result_df['created_utc'].astype('datetime64[s]')
st.dataframe(result_df)

# show selection choice to let user pick which tag they wish to filter out
select = st.sidebar.selectbox('Select a Tag',df_monthly['tag'].unique())

#get the state selected in the selectbox
tag_data = df_monthly[df_monthly['tag'] == select]
tag_table = df_full_data[df_full_data['tag'] == select]
tag_table = tag_table.sort_values(by=['score'],ascending=False)

if st.sidebar.checkbox("Show Analysis by Tag", True, key='1'):
    st.markdown("## **Tag-Level Monthly Threads**")
    fig = px.line(data_frame=tag_data, x= tag_data.index, y='submission_id')
    fig.update_layout(yaxis_title="thread counts")
    st.plotly_chart(fig)

    st.markdown("## **Tag-Level Word Cloud from Thread Titles**")
    wordcloud = WordCloud(background_color='black', colormap='Set2', stopwords = STOPWORDS).generate(' '.join(tag_table['submission_title']))
    st.image(wordcloud.to_array())

    st.markdown("## **Tag-Level Threads**")
    st.dataframe(tag_table)
else:
    st.markdown("## **Monthly Threads**")
    fig = px.line(data_frame= df_monthly, x=df_monthly.index, y='submission_id',color='tag')
    fig.update_layout(yaxis_title="thread counts")
    st.plotly_chart(fig)

    st.markdown("## **Word Cloud from Thread Titles**")
    wordcloud = WordCloud(background_color='black', colormap='Set2', stopwords = STOPWORDS).generate(' '.join(df_full_data['submission_title']))
    st.image(wordcloud.to_array())

    st.markdown("## **Threads**")
    df_full_data_display = df_full_data[['submission_title','created','tag','score','comments','url']]
    st.dataframe(df_full_data_display)
