# where-was-i

Streamlit app to search Google Location History for places

## Dependencies

* `streamlit`
* `holidays`
* `pendulum`

To use the app, you need a Google account you can export your location history from

## Location History

How to obtain the location history:

1. Go to [Google Takeout](https://takeout.google.com)
2. De-select all products
3. Select `Location History`
4. Make sure you select `JSON` in the *Multiple formats* menu
5. Follow the instructions to download the location history (you will obtain a download link to you Gmail address)
6. Extract the archive (depending on your language settings, the folders might be named in your set language)
7. Use the `Location History.json` in folder `Takeout/Location History/`.

## Configuration file format (`yaml`)

```{yaml}
workdays: [1,2,3,4,5] # 0 = Sunday
worktimes: ["06:00", "19:00"] # 24h format, read: from worktimes[0] to worktimes[1]
bank_holidays:
  state: DE # see holidays documentation
  province: BY # see holidays documentation
  extra: 
    - YYYY-MM-DD
    - from: YYYY-MM-DD
    - from: YYYY-MM-DD
      to: YYYY-MM-DD  
vacation:
  - YYYY-MM-DD
  - from: YYYY-MM-DD
  - from: YYYY-MM-DD
    to: YYYY-MM-DD
extra_workdays:
  - YYYY-MM-DD
  - from: YYYY-MM-DD
  - from: YYYY-MM-DD
    to: YYYY-MM-DD  
areas:
  - lat: dd.ddddd
    lng: dd.ddddd
    radius: dddd # in meter
    tag: tag-name
```

## Getting Started

To set up your local development environment, please use a fresh virtual environment.

To create the environment run:

```{bash}
conda env create --name where-was-i --file=environment-dev.yml
```

To activate the environment run:

```{bash}
conda activate where-was-i
```

To update this environment with your production dependencies run:

    conda env update --file=environment.yml

You can now import functions and classes from the module with `import where_was_i`.

### Testing

We use `pytest` as test framework. To execute the tests, please run

    python setup.py test

To run the tests with coverage information, please use

    python setup.py testcov

and have a look at the `htmlcov` folder, after the tests are done.

### Notebooks

To use your module code (`src/`) in Jupyter notebooks (`notebooks/`) without running into import errors, make sure to install the source locally

    pip install -e .

This way, you'll always use the latest version of your module code in your notebooks via `import where_was_i`.

Assuming you already have Jupyter installed, you can make your virtual environment available as a separate kernel by running:

    conda install ipykernel
    python -m ipykernel install --user --name="where-was-i"

Note that we mainly use notebooks for experiments, visualizations and reports. Every piece of functionality that is meant to be reused should go into module code
and be imported into notebooks.

### Distribution Package

To build a distribution package (wheel), please use

    python setup.py dist

this will clean up the build folder and then run the `bdist_wheel` command.

### Debugging Streamlit in VSCode

Add the following configuration to `launch.json`.

See: [Stackoverflow](https://stackoverflow.com/questions/60172282/how-to-run-debug-a-streamlit-application-from-an-ide/64922850#64922850)

```{json}
{
  "name": "Python:Streamlit",
  "type": "python",
  "request": "launch",
  "module": "streamlit.cli",
  "args": [
      "run",
      "${file}",
      "--server.port",
      "8502"            ],
  "console": "internalConsole"
}
```


### Contributions

Before contributing, please set up the pre-commit hooks to reduce errors and ensure consistency

    pip install -U pre-commit && pre-commit install