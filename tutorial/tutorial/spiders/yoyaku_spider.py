# -*- coding: utf-8 -*-
import scrapy
import re
import os
import datetime
import time


class JDramaSpider(scrapy.Spider):
    name = "yoyaku"
    allowed_domains = ["edogawa-yoyaku.jp"]
    start_urls = [
        "http://www.edogawa-yoyaku.jp/edo-user/index-user.html"
    ]
    index_court = 1
    path = "./"
    NUM_OF_MONTH = 2
    dict_court = {}

    def parse(self, response):
        yield scrapy.FormRequest.from_response(response=response, formname="G001", callback=self.login)

    def login(self, response):
        yield scrapy.FormRequest.from_response(response=response, formname="FRM_RSGK001", formdata={
            "ISSUBMIT": "ON",
            "ActionType": "LOGIN",
            "BeanType": "rsv.bean.RSGK001BusinessLogin",
            "ViewName": "RSGK001",
            "ID": "******",
            "PWD": "****",
        }, callback=self.after_login)

    def after_login(self, response):
        yield scrapy.FormRequest.from_response(response=response,
                                               formname="FRM_RSGK001",
                                               formdata={"ISSUBMIT": "ON",
                                                         "ActionType": "INIT",
                                                         "BeanType": "rsv.bean.RSGK301BusinessInit",
                                                         "ViewName": "RSGK301"},
                                               callback=self.go_badminton_catelogy)

    def go_badminton_catelogy(self, response):
        print(response.css(".user_info .txt_large::text")[0].extract())
        yield scrapy.FormRequest.from_response(response=response,
                                               formname="FRM_RSGK301",
                                               formdata={"ISSUBMIT": "ON",
                                                         "ActionType": "LINK_CLICK",
                                                         "BeanType": "rsv.bean.RSGK303BusinessInit",
                                                         "ViewName": "RSGK301",
                                                         "SELECT_DATA": "0014"},
                                               callback=self.get_stadium_list)

    def get_stadium_list(self, response):
        self.create_folder()
        for stadium in response.css("div.bottom button.f_box"):
            select_data = self.get_select_data(stadium.css("::attr(onclick)")[0].extract())
            yield scrapy.FormRequest.from_response(response=response,
                                                   formname="FRM_RSGK303",
                                                   formdata={"ISSUBMIT": "ON",
                                                             "ActionType": "LINK_CLICK",
                                                             "BeanType": "rsv.bean.RSGK304BusinessInit",
                                                             "ViewName": "RSGK303",
                                                             "SELECT_DATA": select_data},
                                                   callback=self.usable_court,
                                                   meta={"index_court": self.index_court,
                                                         "select_court": select_data,
                                                         "month": 0})
            self.dict_court[self.index_court] = stadium.css("::text")[0].extract().encode("utf-8")
            self.index_court += 1

    def get_select_data(self, s):
        match_obj = re.search("'\d+'", s)
        select_data = match_obj.group().replace(" ", "").replace("'", "")
        return select_data

    def back_to_list(self, response):
        yield scrapy.FormRequest.from_response(response=response,
                                               formname="FRM_RSGK304",
                                               formdata={"ISSUBMIT": "ON",
                                                         "ActionType": "RETURN_RSGK303",
                                                         "BeanType": "sv.bean.RSGK303BusinessFromRSGK304",
                                                         "ViewName": "RSGK304",
                                                         "SELECT_DATA": ""},
                                               callback=self.select_court,
                                               meta={"index_court": response.meta["index_court"],
                                                     "select_court": response.meta["select_court"],
                                                     "month": response.meta["month"]})

    def select_court(self, response):
        yield scrapy.FormRequest.from_response(response=response,
                                               formname="FRM_RSGK303",
                                               formdata={"ISSUBMIT": "ON",
                                                         "ActionType": "LINK_CLICK",
                                                         "BeanType": "rsv.bean.RSGK304BusinessInit",
                                                         "ViewName": "RSGK303",
                                                         "SELECT_DATA": response.meta["select_court"]},
                                               callback=self.usable_court,
                                               meta={"index_court": response.meta["index_court"],
                                                     "select_court": response.meta["select_court"],
                                                     "month": response.meta["month"]})

    def usable_court(self, response):
        filename2 = self.path + "/" + "court" + str(response.meta["index_court"]) + '.html'
        with open(filename2, 'wb') as f:
            f.write(response.body)
        yield scrapy.FormRequest.from_response(response=response,
                                               formname="FRM_RSGK304",
                                               formdata={"ISSUBMIT": "ON",
                                                         "ActionType": "LINK_CLICK",
                                                         "BeanType": "rsv.bean.RSGK305BusinessInit",
                                                         "ViewName": "RSGK304",
                                                         "SELECT_DATA": ""},
                                               callback=self.check_calendar,
                                               meta={"index_court": response.meta["index_court"],
                                                     "select_court": response.meta["select_court"],
                                                     "month": response.meta["month"]},
                                               priority=0-response.meta["index_court"]*100)

    def check_calendar(self, response):
        page_court = response.css("div.bottom p:nth-child(2)::text")[0].extract().encode("utf-8")
        if page_court.find(self.dict_court.get(response.meta["index_court"])) < 0:
            yield scrapy.FormRequest.from_response(response=response,
                                                   formname="FRM_RSGK305",
                                                   formdata={"ISSUBMIT": "ON",
                                                             "ActionType": "RETURN_RSGK304",
                                                             "BeanType": "rsv.bean.RSGK304BusinessFromRSGK305",
                                                             "ViewName": "RSGK305",
                                                             "SELECT_DATA": ""},
                                                   callback=self.back_to_list,
                                                   meta={"index_court": response.meta["index_court"],
                                                         "select_court": response.meta["select_court"],
                                                         "month": response.meta["month"]})
        else:
            current_month = datetime.date.today().month
            page_month = int(re.search("\d+\D(\d+)", response.css("td.date strong::text")[0].extract()).group(1))
            interval = page_month-current_month
            if not interval == response.meta["month"]:
                if interval > response.meta["month"]:
                    # pre
                    yield scrapy.FormRequest.from_response(response=response,
                                                           formname="FRM_RSGK305",
                                                           formdata={"ISSUBMIT": "ON",
                                                                     "ActionType": "SEARCH_PREV1M",
                                                                     "BeanType": "rsv.bean.RSGK305BusinessMovePage",
                                                                     "ViewName": "RSGK305"
                                                                     },
                                                           callback=self.check_calendar,
                                                           meta={"index_court": response.meta["index_court"],
                                                                 "select_court": response.meta["select_court"],
                                                                 "month": response.meta["month"]},
                                                           priority=0-response.meta["index_court"]*100-30)
                else:
                    # next
                    yield scrapy.FormRequest.from_response(response=response,
                                                           formname="FRM_RSGK305",
                                                           formdata={"ISSUBMIT": "ON",
                                                                     "ActionType": "SEARCH_NEXT1M",
                                                                     "BeanType": "rsv.bean.RSGK305BusinessMovePage",
                                                                     "ViewName": "RSGK305"
                                                                     },
                                                           callback=self.check_calendar,
                                                           meta={"index_court": response.meta["index_court"],
                                                                 "select_court": response.meta["select_court"],
                                                                 "month": response.meta["month"]},
                                                           priority=0-response.meta["index_court"]*100-30)
            # day
            else:
                filename2 = self.path + "/" + "court" + str(response.meta["index_court"]) + "month" + str(page_month) + '.html'
                with open(filename2, 'wb') as f:
                    f.write(response.body)
                dates = response.css("div.bottom input")
                count = 0
                for date in dates:
                    day = date.css("::attr(value)")[0].extract()
                    yield scrapy.FormRequest.from_response(response=response,
                                                           formname="FRM_RSGK305",
                                                           formdata={"ISSUBMIT": "ON",
                                                                     "ActionType": "SEARCH_POINT_RSGK306",
                                                                     "BeanType": "rsv.bean.RSGK306BusinessInit",
                                                                     "ViewName": "RSGK305",
                                                                     "SELECT_DATA": day
                                                                     },
                                                           callback=self.check_time,
                                                           meta={"index_court": response.meta["index_court"],
                                                                 "select_day": day,
                                                                 "month": response.meta["month"]})
                    count += 1
                count += 1
                if count == len(dates)+1 and (interval+1) < self.NUM_OF_MONTH:
                    yield scrapy.FormRequest.from_response(response=response,
                                                           formname="FRM_RSGK305",
                                                           formdata={"ISSUBMIT": "ON",
                                                                     "ActionType": "SEARCH_NEXT1M",
                                                                     "BeanType": "rsv.bean.RSGK305BusinessMovePage",
                                                                     "ViewName": "RSGK305"
                                                                     },
                                                           callback=self.check_calendar,
                                                           meta={"index_court": response.meta["index_court"],
                                                                 "select_court": response.meta["select_court"],
                                                                 "month": response.meta["month"]+1},
                                                           priority=0-response.meta["index_court"]*100-60)

    def select_date_again(self, response):
        filename2 = self.path + "/" + "back-court" + str(response.meta["index_court"]) + "month" + str(response.meta["request_month"]) + '.html'
        with open(filename2, 'wb') as f:
            f.write(response.body)
        yield scrapy.FormRequest.from_response(response=response,
                                               formname="FRM_RSGK305",
                                               formdata={"ISSUBMIT": "ON",
                                                         "ActionType": "SEARCH_POINT_RSGK306",
                                                         "BeanType": "rsv.bean.RSGK306BusinessInit",
                                                         "ViewName": "RSGK305",
                                                         "SELECT_DATA": response.meta["select_day"]
                                                         },
                                               callback=self.check_time,
                                               meta={"index_court": response.meta["index_court"],
                                                     "select_day": response.meta["select_day"],
                                                     "month": response.meta["month"]})

    def check_time(self, response):
        date = response.css("td.date strong::text")[0].extract()[4:]
        date_match = re.search("(\d+)\D(\d+)\D(\d+)", date)
        current_month = datetime.date.today().month
        page_month = int(date_match.group(2))
        interval = page_month-current_month
        if not interval == response.meta["month"]:
            yield scrapy.FormRequest.from_response(response=response,
                                                   formname="RSGK306",
                                                   formdata={"ISSUBMIT": "ON",
                                                             "ActionType": "RETURN_RSGK305",
                                                             "BeanType": "rsv.bean.RSGK305BusinessFromRSGK306",
                                                             "ViewName": "RSGK306"
                                                             },
                                                   callback=self.select_date_again,
                                                   meta={"index_court": response.meta["index_court"],
                                                         "select_day": response.meta["select_day"],
                                                         "request_month": current_month + response.meta["month"],
                                                         "month": response.meta["month"]})
        else:
            start_time_list, end_time_list = self.get_time_zones(response.css("table#tbl_time tr:nth-child(2) div"))
            filename = self.path + "/" + str(response.meta["index_court"]) + "-" + date_match.group(2) + "-" + date_match.group(3) + ".txt"
            bound = 3
            if datetime.date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))).isoweekday() > 5:
                bound = 4
            with open(filename, "wb") as f:
                count = 0
                while start_time_list:
                    start = start_time_list.pop(0)
                    end = end_time_list.pop(0)
                    if end - start < bound:
                        continue
                    if count == 0:
                        f.write((date + "\n").encode("utf-8"))
                    start_time = datetime.time(9 + (start / 2), (start % 2) * 30, 0, 0)
                    end_time = datetime.time(9 + (end / 2), (end % 2) * 30, 0, 0)
                    output = "\t" + str(start_time) + " - " + str(end_time) + "\n"
                    f.write(output.encode("utf-8"))
                    count += 1

    def get_time_zones(self, s):
        index = 0
        start_time_list = []
        end_time_list = []
        temp = 0
        pre = 0
        while index < len(s):
            match_obj = re.search("'(\d+)'\)", s[index].extract())
            pre = temp
            temp = int(match_obj.group(1))
            if index == 0:
                start_time_list.append(temp - 1)
                pre = temp
            if (temp - pre) > 1:
                end_time_list.append(pre)
                start_time_list.append(temp - 1)
            index += 1
        end_time_list.append(temp)
        return start_time_list, end_time_list

    def closed(self, reason):
        for index in range(1, self.index_court, 1):
            self.merge_file_by_court(index)
            # self.merge_all()

    def merge_file_by_month(self, court, month):
        filename = self.path + "/" + str(court) + "-" + str(month) + ".txt"
        with open(filename, "wb") as f:
            day = 1
            while day <= 31:
                file_to_merge = self.path + "/" + str(court) + "-" + str(month) + "-" + str(day) + ".txt"
                if os.path.isfile(file_to_merge):
                    if not os.stat(file_to_merge).st_size == 0:
                        for line in open(file_to_merge):
                            f.write(line)
                    os.remove(file_to_merge)
                day += 1

    def merge_file_by_court(self, court):
        current_month = datetime.date.today().month
        month = current_month
        while (month - current_month + 1) <= self.NUM_OF_MONTH:
            self.merge_file_by_month(court, month)
            month += 1

        month = current_month
        court_name = self.dict_court.get(court)
        filename = self.path + "/" + unicode(court_name, "utf-8") + ".txt"
        with open(filename, "wb") as f:
            while (month - current_month + 1) <= self.NUM_OF_MONTH:
                file_to_merge = self.path + "/" + str(court) + "-" + str(month) + ".txt"
                for line in open(file_to_merge):
                    f.write(line)
                month += 1

    def create_folder(self):
        folder_name = datetime.datetime.now().strftime('%Y%m%d%H%M')
        self.path += folder_name
        os.makedirs(self.path)






