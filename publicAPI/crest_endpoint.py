"""crest_endpoint.py: collection of public crest endpoints for Prosper"""

import sys
from os import path
from datetime import datetime
from enum import Enum

import ujson as json
from flask import Flask, Response, jsonify
from flask_restful import reqparse, Api, Resource, request

import publicAPI.forecast_utils as forecast_utils
import publicAPI.crest_utils as crest_utils
import publicAPI.exceptions as exceptions
import publicAPI.config as api_config

import prosper.common.prosper_logging as p_logging
import prosper.common.prosper_config as p_config

HERE = path.abspath(path.dirname(__file__))
CONFIG_FILEPATH = path.join(HERE, 'publicAPI.cfg')

CONFIG = p_config.ProsperConfig(CONFIG_FILEPATH)
LOGGER = p_logging.DEFAULT_LOGGER
DEBUG = False

TEST = forecast_utils.LOGGER
## Flask Handles ##
#APP = Flask(__name__)
API = Api()

class AcceptedDataFormat(Enum):
    """enum for handling format support"""
    CSV = 0
    JSON = 1

def return_supported_types():
    """parse AccpetedDataFormat.__dict__ for accepted types"""
    supported_types = []
    for key in AcceptedDataFormat.__dict__.keys():
        if '_' not in key:
            supported_types.append(key.lower())

    return supported_types

def collect_stats(
        endpoint_name,
        args_payload,
        additional_data=None,
        db_name='CREST_stats.json',
        logger=DEFAULT_LOGGER
):
    """save request information for later processing

    Args:
        endpoint_name (str): name of endpoint collecting data
        args_payload (:obj:`dict`): args provided
        additional_data (:obj:`dict`, optional): additional info to save
        db_name (str, optional): tinyDB filename
        logger (:obj:`logging.logger`, optional): logging handle for progress

    Returns:
        None

    """
    pass

## Flask Endpoints ##
@API.representation('text/csv')
def output_csv(data, status, headers=None):
    """helper for sending out CSV instead of JSON"""
    resp = APP.make_response(data)
    resp.headers['Content-Type'] = 'text/csv'
    return resp

class OHLC_endpoint(Resource):
    """Handle calls on OHLC endpoint"""
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(
            'regionID',
            type=int,
            required=True,
            help='regionid for market history API',
            location=['args', 'headers']
        )
        self.reqparse.add_argument(
            'typeID',
            type=int,
            required=True,
            help='typeid for market history API',
            location=['args', 'headers']
        )
        self.reqparse.add_argument(
            'User-Agent',
            type=str,
            required=True,
            help='User-Agent required',
            location=['headers']
        )
        self.reqparse.add_argument(
            'api',
            type=str,
            required=False,
            help='API key for tracking requests',
            location=['args', 'headers']
        )

    def get(self, return_type):
        """GET data from CREST and send out OHLC info"""
        args = self.reqparse.parse_args()
        LOGGER.info(
            'OHLC?regionID={0}&typeID={1}'.format(
                args.get('regionID'), args.get('typeID')
        ))
        LOGGER.debug(args)

        ## Validate inputs ##
        #TODO: error piping
        try:
            crest_utils.validate_id(
                'map_regions',
                args.get('regionID'),
                config=api_config.CONFIG,
                logger=LOGGER
            )
            crest_utils.validate_id(
                'inventory_types',
                args.get('typeID'),
                config=api_config.CONFIG,
                logger=LOGGER
            )
        except Exception as err:
            LOGGER.warning(
                'ERROR: unable to validate type/region ids',
                exc_info=True
            )
            if isinstance(err, exceptions.ValidatorException):
                return err.message, err.status
            else:
                return 'UNHANDLED EXCEPTION', 500

        ## Fetch CREST ##
        #TODO: error piping
        try:
            data = crest_utils.fetch_market_history(
                args.get('regionID'),
                args.get('typeID'),
                config=api_config.CONFIG,
                logger=LOGGER
            )
        except Exception as err:
            LOGGER.warning(
                'ERROR: unable to parse CREST data',
                exc_info=True
            )
            if isinstance(err, exceptions.ValidatorException):
                return err.message, err.status
            else:
                return 'UNHANDLED EXCEPTION', 500

        ## Format output ##
        message = crest_utils.OHLC_to_format(
            data,
            return_type
        )

        return message

DEFAULT_RANGE = CONFIG.get('CREST', 'prophet_range')
MAX_RANGE = CONFIG.get('CREST', 'prophet_max')
class ProphetEndpoint(Resource):
    """Handle calls on Prophet endpoint"""
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(
            'regionID',
            type=int,
            required=True,
            help='regionid for market history API',
            location=['args', 'headers']
        )
        self.reqparse.add_argument(
            'typeID',
            type=int,
            required=True,
            help='typeid for market history API',
            location=['args', 'headers']
        )
        self.reqparse.add_argument(
            'User-Agent',
            type=str,
            required=True,
            help='User-Agent required',
            location=['headers']
        )
        self.reqparse.add_argument(
            'api',
            type=str,
            required=True,
            help='API key for tracking requests',
            location=['args', 'headers']
        )
        self.reqparse.add_argument(
            'range',
            type=int,
            required=False,
            help='Range for forecasting: default=' + DEFAULT_RANGE + ' max=' + MAX_RANGE,
            location=['args', 'headers']
        )

    def get(self):
        args = self.reqparse.parse_args()
        LOGGER.info(
            'prophet?regionID={0}&typeID={1}&range={2}'.format(
                args.get('regionID'), args.get('typeID'), args.get('range')
        ))
        LOGGER.debug(args)

        ## Validate inputs ##
        try:
            crest_utils.validate_id(
                'map_regions',
                args.get('regionID'),
                config=api_config.CONFIG,
                logger=LOGGER
            )
            crest_utils.validate_id(
                'inventory_types',
                args.get('typeID'),
                config=api_config.CONFIG,
                logger=LOGGER
            )
        except Exception as err:
            LOGGER.warning(
                'ERROR: unable to validate type/region ids',
                exc_info=True
            )
            if isinstance(err, exceptions.ValidatorException):
                return err.message, err.status
            else:
                return 'UNHANDLED EXCEPTION', 500

        #TODO: validate range
        forecast_range = DEFAULT_RANGE
        ## Fetch CREST ##
        #TODO: error piping
        try:
            data = forecast_utils.fetch_extended_history(
                args.get('regionID'),
                args.get('typeID')
            )
        except Exception as err:
            LOGGER.warning(
                'Unable to fetch data from archive',
                exc_info=True
            )
            data = crest_utils.fetch_market_history(
                args.get('regionID'),
                args.get('typeID')
            )
        data = forecast_utils.build_forecast(
            data,
            forecast_range
        )
        ## Format output ##
        message = forecast_utils.data_to_format(
            data,
            return_type
        )

        return message
## Flask Endpoints ##
API.add_resource(
    OHLC_endpoint,
    CONFIG.get('ENDPOINTS', 'OHLC') + '.<return_type>'
)

API.add_resource(
    ProphetEndpoint,
    CONFIG.get('ENDPOINTS', 'prophet') + '.<return_type>'
)


class CrestEndpointException(Exception):
    """baseclass for crest_endpoint exceptions"""
    pass
class BadStatus(CrestEndpointException):
    """unexpected status raised"""
    pass


