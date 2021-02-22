import os

from dothttp.exceptions import *
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
req_base_path = f"{dir_path}/requests"
sub_base_path = f"{dir_path}/substitution"
neg_base_path = f"{dir_path}/negations"


class NegativeScenarios(TestBase):

    def test_http_notfound(self):
        with self.assertRaises(HttpFileNotFoundException):
            self.get_request("/tmp/json")

    def test_property_file_not_found(self):
        with self.assertRaises(PropertyFileNotFoundException):
            self.get_request(f"{req_base_path}/pass2.http", prop="/tmp/test")

    def test_property_file_not_json(self):
        with self.assertRaises(PropertyFileNotJsonException):
            self.get_request(f"{req_base_path}/pass2.http", prop=f"{req_base_path}/pass2.http")

    def test_property_not_found(self):
        with self.assertRaises(PropertyNotFoundException):
            self.get_request(f"{sub_base_path}/multipleprop.http", prop=f"{sub_base_path}/prop1.json")

    def test_commmand_line_not_found(self):
        with self.assertRaises(CommandLinePropError):
            self.get_request(f"{sub_base_path}/multipleprop.http", properties=["ranga"])

    def test_data_payload_not_valid(self):
        with self.assertRaises(PayloadDataNotValidException):
            self.get_request(f"{neg_base_path}/datapayload.http")

    def test_data_file_not_found(self):
        with self.assertRaises(DataFileNotFoundException):
            self.get_request(f"{neg_base_path}/datafilenotfound.http")

    def test_data_file_not_found(self):
        with self.assertRaises(DataFileNotFoundException):
            self.get_request(f"{neg_base_path}/datafilenotfound.http")

    def test_property_file_not_compatiable_json(self):
        with self.assertRaises(PropertyFileException):
            self.get_request(f"{sub_base_path}/multipleprop.http", prop=f"{neg_base_path}/invalidpropertyfile.json")

    def test_infile_property_raise(self):
        with self.assertRaises(HttpFileException):
            self.get_request(f"{sub_base_path}/infileproperty.http")

    def test_property_with_multiple_val_for_single(self):
        with self.assertRaises(HttpFileException):
            self.get_request(f"{neg_base_path}/infileproperty2.http")
