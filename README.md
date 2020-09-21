# iCerebro

## Usage
Open webpage, create an account, set bot settings to your liking, run the bot

In the current UI there are no buttons to go back to settings after the first setup, to change them go to the following addresses:
 - `<base_url>/bot/settings/<bot_username>/<settings_name>/`
 - `<base_url>/bot/run/settings/<bot_username>/`

## Install
To run locally you need Firefox, python3, and all the packages listed in [requirements.txt](./requirements.txt), with pip installed run `pip install -r requirements.txt` to install them


It may be run on windows if you set a path in the environment as GECKODRIVER_PATH to a geckodriver.exe file appropriate for the installed version of firefox


## Run Locally
DATABASE_URL needs to be set on the environment, on linux run:

```bash
export DATABASE_URL=<database_url>
```

replacing `<database_url>` with the actual url, not provided here to avoid misuse of the project database

Then choose a port and run:

```bash
python manage.py runserver 0.0.0.0:<port>
```

Finally, open in your browser of preference the url `0.0.0.0:<port>`

If you want to see the browser as iCerebro use it in your bot settings set the option "disable_image_load" to False before running it

## Setup own database
TODO