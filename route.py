#!/usr/bin/env python
# coding: utf-8

""" 断开连接，重新取得IP(路由器型号: CVR100W).
依赖: Tronado(http://www.tornadoweb.org)

1. 得到当前的WAN IP.
2. 登录.
3. 断开连接.
4. 重新连接.
5. 重复1.

"""

import re
import time
import urllib
from hashlib import md5

from tornado.httpclient import HTTPClient, HTTPRequest


ROUTE_ADDR = "https://192.168.1.1:8888"


class HTTPHelper(object):
    """HTTP请求
    使用tornado.httpclient库.
    
    """
    def __init__(self, url, method="POST", body=None):
        self._url = url
        self._method = method
        self._body = body or dict()
        self.client = HTTPClient()
        self._response = None


    def fetch(self, url=None, validate_cert=False, **kwargs):
        url = url or self._url
        body = self._method == "POST" and urllib.urlencode(self._body) or None
        
        self._request = HTTPRequest(
            url=url, method=self._method,
            body=body,
            validate_cert=validate_cert,
            **kwargs)
        self._response = self.client.fetch(request=self._request)
        return self._response


    @property
    def body(self):
        return self._response.body


    @property
    def response(self):
        return self._response



class Regex(object):
    @staticmethod
    def match(pattern, body, multi=False):
        assert pattern, "Pattern is null."
        want = re.findall(pattern, body)
        if not multi:
            want = want and want[-1] or ""
        
        return want



class RouteLogin(object):
    def __init__(self, name, passwd, url=None, relogin=False):
        self._name = name
        self._passwd = passwd
        self._url = url or "%s/login.cgi" % ROUTE_ADDR
        self._sessionid = None
        self._route_login(relogin)
        
        
    def _route_login(self, relogin):
        post = {"change_action": "",
                "enc": 1,
                "gui_action": "",
                "id": "",
                "login_type": 2,
                "pwd": self._cisco_md5(self._passwd),
                "submit_button": "login",
                "submit_type": relogin and "login_continue" or "", 
                "timeout_page": "",
                "user": self._name,
                "wait_time": 0}
        client = HTTPHelper(self._url, body=post)
        response = client.fetch()
        self._sessionid = self._regex(response.body)


    @property
    def sessionid(self):
        return self._sessionid


    def _regex(self, html):
        pattern = r"wizard_id_st=\"(\w+)\""
        sessionid = Regex.match(pattern, html)
        
        return sessionid


    def _cisco_md5(self, s):
        result = ""
        s_len = len(s)
        tmp = s_len < 10 and "%s0%d" % (s, s_len) or "%s%d" % (s, s_len)
        s_len += 2

        for i in range(64):
            loc = i % s_len
            result += tmp[loc: loc + 1]

        return md5(result).hexdigest()


        
class RouteHelper(object):
    def __init__(self, name=None, passwd=None):
        self._name = name or "cisco"
        self._passwd = passwd or "cisco"
        self._sessionid = None
        self._login()


    def _login(self):
        rl = RouteLogin(self._name, self._passwd)
        if rl.sessionid:
            self._sessionid = rl.sessionid
        else:
            rl = RouteLogin(self._name, self._passwd, relogin=True)
            assert rl.sessionid, "Login failed."
            self._sessionid = rl.sessionid


    def disconnect(self):
        self._submit("disconnect_pppoe")


    def connect(self):
        self._submit("connect_pppoe")


    def get_wan_ip(self):
        client = HTTPHelper("%s/" % ROUTE_ADDR, method="GET")
        response = client.fetch()
        pattern = r"MESS_RIGHT>([0-9]+(?:\.[0-9]+){3})<"
        ips = Regex.match(pattern, response.body, multi=True)
        return ips


    def _submit(self, sub_type):
        assert sub_type in ("connect_pppoe", "disconnect_pppoe"), "Only support this list."
        post = {
            "change_action": "gozila_cgi",
            "fresh_rate": 0,
            "submit_button": "system",
            "submit_type": sub_type}
        url = "%s/apply.cgi;session_id=%s" % (ROUTE_ADDR, self._sessionid)
        client = HTTPHelper(url, method="POST", body=post)
        client.fetch()


    @property
    def connected(self):
        # TODO 是否已经连接
        pass



def run():
    r = RouteHelper(name="admin", passwd="admin")
    print "当前IP:", r.get_wan_ip()
    r.disconnect()
    time.sleep(1)
    r.connect()
    time.sleep(1)
    print "新的IP:", r.get_wan_ip()



if __name__ == "__main__":
    run()
