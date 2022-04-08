import os
from typing import Union, Any

from dothttp import Allhttp, BaseModelProcessor, Http
from dothttp.request_base import dothttp_model
from ..models import Command, Result, BaseHandler, DothttpTypes


class TypeFromPos(BaseHandler):
    name = "/content/type"

    def get_method(self):
        return TypeFromPos.name

    def run(self, command: Command) -> Result:
        position: Union[None, int] = command.params.get("position", None)
        filename: Union[str, None] = command.params.get('filename', None)
        content: Union[str, None] = command.params.get('content', None)
        if not isinstance(position, int):
            return Result(id=command.id,
                          result={"error_message": f"position should be int", "error": True})
        if filename:
            if not isinstance(filename, str):
                return Result(id=command.id,
                              result={"error_message": f"filename should be should be string", "error": True})
            if not os.path.isfile(filename):
                return Result(id=command.id,
                              result={"error_message": f"non existant file", "error": True})
        if not filename and not content:
            return Result(id=command.id,
                          result={"error_message": f"filename or content should be available", "error": True})
        if content and not isinstance(content, str):
            return Result(id=command.id,
                          result={"error_message": f"content should be string", "error": True})
        if filename:
            model: Allhttp = dothttp_model.model_from_file(filename)
        else:
            model: Allhttp = dothttp_model.model_from_str(content)
        try:
            return Result(id=command.id, result=self.figure_n_get(model, position))
        except Exception as e:
            return Result(id=command.id, result={"error_message": f"unknown Exception {e}", "error": True})

    def figure_n_get(self, model: Allhttp, position: int) -> dict:
        if self.is_in_between(model, position):
            index = 0
            for index, pick_http in enumerate(model.allhttps):
                if self.is_in_between(pick_http, position):
                    if dot_type := self.pick_in_http(pick_http, position):
                        name = str(index + 1)
                        base = None
                        base_position = None
                        ret = {}
                        if dot_type == DothttpTypes.SCRIPT:
                            # vscode can provide suggestions for
                            # only javascript
                            # will only useful be for that specific scenario
                            ret.update({
                                "start": pick_http.script_wrap._tx_position,
                                "end": pick_http.script_wrap._tx_position_end
                            })
                        if namewrap := pick_http.namewrap:
                            name = namewrap.name
                            base = namewrap.base
                            if base:
                                try:
                                    base_position = BaseModelProcessor.get_target(base, model.allhttps)._tx_position
                                except:
                                    pass
                        ret.update({"type": dot_type.value, "target": name, "target_base": base,
                                    "base_start": base_position
                                    })
                        return ret
        return {"type": DothttpTypes.COMMENT.value}

    @staticmethod
    def pick_in_http(pick_http: Http, position: int) -> DothttpTypes:
        self = TypeFromPos
        if pick_http:
            # order
            # name, extra args, url, basic/digest auth, certificate, query or headers, payload, output, script_wrap
            if namewrap := pick_http.namewrap:
                if self.is_in_between(namewrap, position):
                    return DothttpTypes.NAME
            if args := pick_http.extra_args:
                for arg in args:
                    if self.is_in_between(arg, position):
                        return DothttpTypes.EXTRA_ARGS
            if url_wrap := pick_http.urlwrap:
                if self.is_in_between(url_wrap, position):
                    return DothttpTypes.URL
            if auth_wrap := pick_http.authwrap:
                if auth_wrap.basic_auth:
                    if self.is_in_between(auth_wrap.basic_auth, position):
                        return DothttpTypes.BASIC_AUTH
                elif pick_http.authwrap.digest_auth:
                    if self.is_in_between(pick_http.authwrap.digest_auth, position):
                        return DothttpTypes.DIGEST_AUTH
                elif pick_http.authwrap.ntlm_auth:
                    if self.is_in_between(pick_http.authwrap.digest_auth, position):
                        return DothttpTypes.NTLM_AUTH
            if certificate := pick_http.certificate:
                if self.is_in_between(certificate, position):
                    return DothttpTypes.CERTIFICATE
            if lines := pick_http.lines:
                for line in lines:
                    if self.is_in_between(line, position):
                        if self.is_in_between(line.header, position):
                            return DothttpTypes.HEADER
                        return DothttpTypes.URL_PARAMS
            if payload := pick_http.payload:
                if self.is_in_between(payload, position):
                    if payload.data:
                        return DothttpTypes.PAYLOAD_DATA
                    elif payload.datajson:
                        return DothttpTypes.PAYLOAD_ENCODED
                    elif payload.json:
                        return DothttpTypes.PAYLOAD_JSON
                    elif payload.file:
                        return DothttpTypes.PAYLOAD_FILE
                    elif payload.fileswrap:
                        return DothttpTypes.PAYLOAD_MULTIPART
                    return DothttpTypes.PAYLOAD_JSON
            if output := pick_http.output:
                if self.is_in_between(output, position):
                    return DothttpTypes.OUTPUT
            if script_wrap := pick_http.script_wrap:
                if self.is_in_between(script_wrap, position):
                    return DothttpTypes.SCRIPT

    @staticmethod
    def is_in_between(model: Any, position):
        return model and model._tx_position < position < model._tx_position_end
