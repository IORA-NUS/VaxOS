import os

prod_settings = {
    'debug': False,
}

dev_settings = {
    'debug': False,
    'port': 8050
}

local_settings = {
    'debug': True,
    'port': 8050
}

if os.environ.get("DASH_ENV") == "prod":
    settings = prod_settings
elif os.environ.get("DASH_ENV") == "dev":
    settings = dev_settings
else:
    settings = local_settings
