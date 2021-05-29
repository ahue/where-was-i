
import base64
from functools import reduce
from json import loads
from typing import Dict, List

import holidays
import numpy as np
import pandas as pd
import streamlit as st


def filter_year(df: pd.DataFrame, year: int):
    """
    Computes at `time` columns from `timestampMs` and returns a copy of `df`, filtered on `year`

    Parameters
    ----------
    df: pandas.DataFrame
        The DataFrame to process
    year: int
        The year to filter `df`on

    Returns
    ------
    The filtered data frame, containing an additional column `time`.

    """

    df = df.copy()
    # parse time
    df.loc[:, "time"] = pd.to_datetime(
        pd.to_numeric(df.timestampMs), unit='ms').dt.tz_localize(
            'UTC').dt.tz_convert('Europe/Berlin')
    
    df = df[df.time.dt.year == year]

    return df


# %%
def clean_lhdf(df: pd.DataFrame):
    """
    Removes unneccessary columms from the location history data frame and computes new required columns

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame to process

    Returns
    -------
    Copy of `df`, altered the following way:
    * Colums removed
        * `activity`
        * `altitude`
        * `heading`
    * Columns expected in `df`
        * `time`
        * `latitudeE7`
        * `longitudeE7`
    * Columns added
        * `date` (Format `YYYY-MM-DD`)
        * `weekday` (Format: `0-6`; 0 = Sunday)
        * `daytime` (Format: HH:ii, 24h style)
        * `lat` (Format: dd.ddddd)
        * `lon` (Format: dd.ddddd)
    """


    df = df.copy()
    # Drop unneccessary cols
    df.drop(labels=["activity", "altitude", "heading"], axis=1, inplace=True)



    # compute time cols
    df.loc[:, "date"] = df.time.dt.strftime("%Y-%m-%d")
    df.loc[:, "weekday"] = df.time.dt.strftime("%w") #was: %u
    df.loc[:, "daytime"] = df.time.dt.strftime("%H:%M")

    df.loc[:,"lat"] = pd.to_numeric(df.latitudeE7) / 1e7
    df.loc[:,"lng"] = pd.to_numeric(df.longitudeE7) / 1e7

    return df

def year_mask(df: pd.DataFrame, year: int):
    """
    Returns a boolean mask to a given DataFrame using

    Parameters
    ----------
    df : pandas.DataFrame
        Expected to have a datetime column `time`
    year : int
        Year to masked


    Returns
    -------
    Boolean mask of size `df.shape[0]`
    """
    return df.time.dt.year == year

def vacation_days(cfg: Dict):
    """
    Produces a list of dates from the vacation configuration by rolling
    from and to dates out.

    Parameters
    ----------
    cfg : Dict
        Configuration dictionary; Expects key `vacation` that contains list of 
        vacation entries of the form
        "YYYY-MM-DD" or {"from": YYYY-MM-DD} or {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"} 
    
    Returns
    -------
    List of "YYYY-MM-DD"
    """

    vacation = []
    for vac in cfg["vacation"]:
        start = end = None
        if type(vac) == dict and "from" in vac.keys():
            start = vac["from"]
          
            if "to" in vac.keys():
                end = vac["to"]
            else:
                end = start
        
        else:
            start = vac
            end = start
        
        vacation += pd.date_range(
            start=start, 
            end=end
            ).to_series().dt.strftime("%Y-%m-%d").to_list()

    return vacation

def vacation_mask(df: pd.DataFrame, cfg: Dict):
    """
    Creates a boolean mask on the provided `df` based on the vacation data provided in `cfg`

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to build the mask for
    cfg : Dict
        see vacation_days(*args, **kwargs)

    Returns
    -------
    A `pandas.Series` boolean mask of size `df.shape[0]`
    """

    vacation = vacation_days(cfg)

    mask = df.date.isin(vacation) == False 
    return mask

def worktime_mask(df: pd.DataFrame, cfg: Dict):
    """
    Creates a boolean mask on the provided `df`based on the worktimes provided in `cfg`

    Parameters
    ----------
    df : `pandas.DataFrame`
        The DataFrame to build the mask for
    cfg : Dict
        Expects a key `worktimes` that contains a list of length 2
        * index 0: start worktime on a work day, format HH:ii
        * index 1: end worktime on a work day, format HH:ii

    Returns
    -------
    A `pandas.Series` boolean mask of size `df.shape[0]`
    """
    return df.daytime.between(cfg["worktimes"][0], cfg["worktimes"][1])

def workdays_mask(df: pd.DataFrame, cfg: Dict):
    """
    Creates a boolean mask on the provided `df`based on the work days provided in `cfg`
    Work days are typical week days for work.

    Parameters
    ----------
    df : `pandas.DataFrame`
        The DataFrame to build the mask for
    cfg : Dict
        Expects a key `workdays` that contains a list of `int` with values 0 to 6

    Returns
    -------
    A `pandas.Series` boolean mask of size `df.shape[0]`
    """
    return df.weekday.astype(int).isin(cfg["workdays"])

def bank_holidays(cfg: Dict, year: int):
    """
    Creates a list of holidays, based on the location configuration provided

    Parameters
    ----------
    cfg : Dict
        Expects the following structure:
            {
                "bank_holidays":
                    {
                        "state": XX
                        "province": XX
                    }
            }
    year : int
        The year to create the holidays for 

    Returns
    -------
    `list` of `str` in format `YYYY-MM-DD`

    """

    return map(lambda x: x.strftime("%Y-%m-%d"), 
        getattr(holidays, cfg["bank_holidays"]["state"])(
            years=year, 
            prov=cfg["bank_holidays"]["province"]).keys())
    

def bank_holiday_mask(df: pd.DataFrame, cfg: Dict, year: int):
    """ 
    Creates a boolean mask on the provided `df`based on holidays configured via `cfg`
    see `bank_holidays`

    Parameters
    ----------
    df : `pandas.DataFrame`
        The DataFrame to build the mask for
    cfg : Dict
        see `bank_holidays(*args, **kwargs)`
    year : int
        The year to create the holidays for 

    Returns
    -------
    A `pandas.Series` boolean mask of size `df.shape[0]`
    """

    mask = df.date.isin(
        bank_holidays(cfg, year)
        ) == False

    return mask

def apply_masks(df, masks: List):
    """
    Applies a list of boolean masks to a filter a data frame

    Parameters
    ----------
    df : `pandas.DataFrame`
        The DataFrame to filter
    masks:
        List of `pandas.Series` boolean filter masks

    Returns
    -------
    Filtered copy of the provided DataFrame
    """

    df = df.copy()
    mask = reduce(lambda i,j: i & j, masks)
    return df[mask]

def assign_areas(df: pd.DataFrame, cfg: Dict):
    """
    Processes the provided DataFrame and assigns the rows the areas found in `cfg`. 
    If multiple areas would match a row the one first identified is used.

    Parameters
    ----------
    df : `pandas.DataFrame`
        The DataFrame to process
    cfg:
        Dictionary containing the areas to search for. Following structure is expected:
        ```
        areas:
        - tag:
          radius
          lat
          lng
        ```

    Returns
    -------
    Copy of `df` with three additional columns
    * `dist`: Distance in meter between row coordinate and area coordinate
    * `area`: Name of the area
    * `in_area`: Boolean mask that marks rows as having an area assigned

    """

    df = df.copy()
    areas = cfg["areas"]

    # compute distances and wether within area
    df.loc[:, "in_area"] = False
    for area_idx in range(0, len(areas)):
        mask = df.in_area == False
        df.loc[mask, 'distTuple'] = (
            df.loc[mask,:].apply(
                lambda x: list(map(lambda y: (y, areas[area_idx]["tag"] if y < areas[area_idx]['radius'] else None),
                                                          [haversine(x['lat'],
                                                          x['lng'], 
                                                          areas[area_idx]['lat'],
                                                          areas[area_idx]['lng'])]) )[0],axis=1).values)
        df.loc[:, 'dist'] = df.distTuple.apply(lambda x: x[0])
        df.loc[:, 'area'] = df.distTuple.apply(lambda x: x[1])
        df.loc[:, "in_area"] = df.area.isna() == False

    return df


def visit_no(df, timedelta="3h"):
    """
    Adds a visit number to the data frame

    Parameters
    ----------
    df : `pandas.DataFrame`
        The DataFrame to process
    timedelta:
        The time delta between two rows to consider the second row being a new visit. See `pandas.Timedelta`.

    Returns
    -------
    Copy of `df` filtered on only rows in an area with additional column `visitNo` that identifies the visit.

    """

    df = df[df.in_area].copy()

    area_change = (df.area != df.area.shift()).astype(int)
    revisit_same_area = (
        (df.time - df.time.shift() > pd.Timedelta(timedelta)) &
        (df.area == df.area.shift()) & 
        (df.date == df.date.shift()) 
        ).astype(int)
    date_change_in_same_area = (
        (df.date != df.date.shift()) &
        (df.area == df.area)
    )

    df.loc[:, "visitNo"] = (area_change + revisit_same_area + date_change_in_same_area).cumsum()

    return df

def haversine(lat1,lon1,lat2,lon2, to_radians = True, earth_radius =6371):
    """
    Computes distance in meters between (lat1,lon1) and (lat2,lon2)

    Parameters
    ----------
    lat1 : `float`
        Latitude of first coordinate
    lon1 : `float`
        Longitude of first coordinate
    lat2 : `float`
        Latitude of second coordinate
    lon1 : `float`
        Longitude of first coordinate
    to_radians: `boolean` (default=True)
        Whether to transform provided lat/lon values to radians
        TODO when needed?
    earth_radis: `float|int` (default=6371)
        Earth radius in km

    Returns
    -------
    `float` distance in meters between provided coordinates


    """
    if to_radians:
        lat1,lon1,lat2,lon2 = np.radians([lat1,lon1,lat2,lon2])

    a = np.sin((lat2-lat1)/2.0)**2+ np.cos(lat1) * np.cos(lat2) * np.sin((lon2- 
    lon1)/2.0)**2

    return earth_radius *2 * np.arcsin(np.sqrt(a))*1000 # return distance in meter

def get_table_download_link(df, href_text="Download csv file"):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    
    Parameters
    ----------
    df : `pandas.DataFrame`
      DataFrame to provide download link for
    href_text: `str`
      The link text to display 

    Returns
    -------
    `str` Url to download the file

    Thanks to godot63, see https://discuss.streamlit.io/t/how-to-download-file-in-streamlit/1806

    """
    csv = df.to_csv(index=True)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}">{href_text}</a>'

    return href
