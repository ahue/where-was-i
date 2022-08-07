#%%

from datetime import datetime
from io import StringIO
from json import load
import ijson
import bigjson

import pandas as pd
import pendulum as pm
import streamlit as st
import yaml
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode


from where_was_i import lib

#%%
st.title("Where was I?")

base_path = "../../data/"

st.markdown('## Setup')

with st.form(key="my_form"):
    st.markdown("### Year filter")
    year = st.number_input("Year", value=pm.today().year-1, min_value = 1990, max_value=datetime.today().year, step=1, format="%d")

# st.write(year_start_ms)

    st.markdown("### Configuration")

    ul_cfg_file = st.file_uploader("Select configuration file")

    st.markdown("### Location History")

    ul_lh_file = st.file_uploader("Select location history file"
        #, accept_multiple_files=True
    )

    submit = st.form_submit_button(label="Go")

if not ul_lh_file or not ul_cfg_file or not submit:
    st.warning('Complete the setup and press "Go".')
    st.stop()
st.success('Setup complete. Lets go!')


# objects = ijson.items(ul_lh_file,"locations.item")

# if objects:
#   st.write("Created objects variable")

# with st.empty():
#   lh_list = []
#   i = 0
#   for o in objects:
#     if i % 100000 == 0:
#       st.markdown(f"""items processed: `{i}`

# items found: `{len(lh_list)}`""")
#     if o["timestampMs"] >= year_start_ms and o["timestampMs"] < year_end_ms:
#       lh_list.append(o)
#     i += 1


ul_cfg_file_stringio = StringIO(ul_cfg_file.getvalue().decode('utf-8'))
cfg_s = ul_cfg_file_stringio.read()

cfg = yaml.safe_load(cfg_s)

st.markdown(f"""
```
{cfg_s}
```""")

@st.cache
def load_lh(fh):
    # https://pythonspeed.com/articles/json-memory-streaming/
    lh = ijson.items(fh, "locations.item")
    # lh = bigjson.load(fh)['locations']
    records = []
    cur_year = None
    attributes = set()
    for record in lh:
        if cur_year != int(record['timestamp'][0:4]):
            cur_year = int(record['timestamp'][0:4])
            print(cur_year)
        if cur_year != year:
            continue
        attributes.update(record.keys())
        records.append({
            "latitudeE7": record['latitudeE7'],
            "longitudeE7": record['longitudeE7'],
            "accuracy": record['accuracy'],
            "timestamp": record['timestamp'] #pm.parse(record['timestamp'])
        })
    st.write(attributes) # will cause CachedStFunctionWarning 
    df = pd.DataFrame.from_records(records)
    # lh = load(fh)["locations"]
    # df = pd.DataFrame(lh)
    return df 

with st.spinner("Loading location data"):
    lhdf = load_lh(ul_lh_file)

st.write(lhdf.head())

@st.cache(suppress_st_warning=True)
def process_lh(df, cfg, year):
    st.write(f"Starting... ({df.shape[0]} rows)")
    df = lib.filter_year(df, year)
    st.write(f"Filtered by year ({df.shape[0]} rows)")
    df = lib.clean_lhdf(df)
    st.write(f"Cleaning complete ({df.shape[0]} rows)")
    df = lib.apply_masks(df, [
        # year_mask(lhdf, year),
        lib.vacation_mask(df, cfg),
        lib.worktime_mask(df, cfg), 
        lib.bank_holiday_mask(df, cfg, year), 
        lib.workdays_mask(df, cfg),
    ])
    st.write(f"Filtering complete ({df.shape[0]} rows)")
    df = lib.assign_areas(df, cfg)
    st.write(f"Area assignment complete ({df.shape[0]} rows)")
    lhdf_in_area = lib.visit_no(df)
    st.write(f"Visit computation complete ({lhdf_in_area.shape[0]} rows)")
    return lhdf_in_area

with st.spinner(text="Computation in progress"):
    lhdf_in_area = process_lh(lhdf, cfg, year)

st.markdown("## Statistics")

st.markdown("### Areas")

map_area = pd.DataFrame(cfg["areas"])
map_area.rename(columns={"lng": "lon"}, inplace=True)

st.write(map_area)

st.map(map_area)

# Visit statistics
visits = lhdf_in_area.groupby(["date", "visitNo", "area"])["time"].agg(stayed=lambda x: max(x)-min(x), min="min", max="max")
#lhdf.time.agg(func=lamda x: max(x) - min(x))
visits.loc[:, "stayed"] = visits.loc[:, "stayed"].astype('timedelta64[m]').astype(int)/60
visits = visits.reset_index()
visits.loc[:, "longest_stay"] = visits.groupby("date")["stayed"].transform("max") == visits.stayed

visit_cnts = visits[visits.loc[:,"longest_stay"]].groupby("area").agg(count=pd.NamedAgg("stayed", aggfunc = "count"))
visit_cnts.rename(columns={"count":"Days in area"}, inplace=True)


st.write(visit_cnts.T)


st.markdown(lib.get_table_download_link(visits), unsafe_allow_html=True)

try: 
    st.write(visits[visits.longest_stay].pivot(index="date", columns="area", values="stayed"))
except:
    AgGrid(visits)



# Actual Vacation Days
vacation = pd.Series(lib.vacation_days(cfg))

vacation = vacation[vacation.isin(lib.bank_holidays(cfg, year)) == False]
vacation = vacation[pd.to_datetime(vacation).dt.strftime("%w").astype(int).isin(cfg["workdays"])]

st.markdown(f"### Vaction Days ({len(vacation)})")

st.write(vacation)

# %%
