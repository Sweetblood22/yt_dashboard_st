import os
import zipfile

if not os.path.exists('data'):
    os.mkdir('data')
if not os.path.exists('data/archive'):
    os.mkdir('data/archive')

DATAURL = "https://www.kaggle.com/datasets/kenjee/ken-jee-youtube-data/download?datasetVersionNumber=2"

with zipfile.ZipFile('data/archive.zip') as zip_ref:
    zip_ref.extractall('data/archive')

with open("data/archive/Aggregated_Metrics_By_Video.csv", "r") as fp:
    lines = fp.readlines()
    # replace header
    lines[0] = 'Video,Video title,Video publish time,Comments added,Shares,Dislikes,Likes,Subscribers lost,Subscribers gained,RPM (USD),CPM (USD),Average percentage viewed (%),Average view duration,Views,Watch time (hours),Subscribers,Your estimated revenue (USD),Impressions,Impressions click-through rate (%)\n'
    # remove first line after header which contains totals
    lines.pop(1)
with open("data/archive/Aggregated_Metrics_By_Video.csv", "w") as fp:
    fp.writelines(lines)
