# coding=utf-8
import json
import os
import time
import math

import requests
import csv


class KzzSpider:

    def __init__(self, order='desc', filtered_below_price=112, filtered_below_rate=0.15, target='data'):
        self.kzz_url = "http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get?type=KZZ_LB2.0&token=70f12f2f4f091e459a279469fe49eca5&cmd=&st=STARTDATE&js={data:(x),font:(font)}"
        self.target = target
        if order.lower() == 'desc':
            self.date_desc = True
        else:
            self.date_desc = False
        self.price = filtered_below_price
        self.rate = filtered_below_rate

    def parse_content(self, content):  # 提取数据
        content = content.replace("font", "\"font\"", 1).replace("data", "\"data\"", 1);  # convert to valid json
        dict_ret = json.loads(content)
        mappings = dict_ret["font"]["FontMapping"]
        for i, val in enumerate(mappings):
            content = content.replace(val["code"], str(val["value"]))  # decode
        dict_ret = json.loads(content)
        bonds = dict_ret["data"]
        with open("kzz.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(bonds, ensure_ascii=False, indent=2))
        total = len(bonds)
        print("一共获取 " + str(total) + " 条可转债！kzz.json 保存成功")
        return bonds, total

    def init_folder(self, folder):  # Create target folder under current folder
        # 如果目标文件夹已存在，清空文件夹（先清空后删除再创建）
        pathd = os.path.join(os.getcwd(), self.target, folder)
        if os.path.exists(pathd):  # 判断文件夹是否存在
            for root, dirs, files in os.walk(pathd, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))  # 删除文件
                for name in dirs:
                    os.rmdir(os.path.join(root, name))  # 删除文件夹
            os.rmdir(pathd)  # 删除目标文件夹
        os.makedirs(pathd)  # 创建目标文件夹
        return pathd

    def save_content_list(self, folder, name, content_list, sep=','):  # 保存全部
        file = os.path.join(folder, name)
        if os.path.exists(file):
            os.remove(file)  # clean up
        with open(file, "a", encoding="utf-8", newline='\n') as f:
            wr = csv.writer(f, dialect='excel', delimiter=sep)
            self.save_title(wr, sep)
            for bond in content_list:
                self.format(bond)
                self.save_item(wr, bond)
        print("保存成功: " + file)

    def format(self, bond):  # Replace '-' with 0
        if bond["ZGJZGJJZ"].strip() == '-':
            bond["ZGJZGJJZ"] = 0;
        if bond["YJL"].strip() == "-":
            bond["YJL"] = '0';
        if bond["ZQNEW"].strip() == '-':
            bond["ZQNEW"] = 0;

    def save_filtered_content(self, folder, name, content_list, price=112, rate=0.15, sep=','):  # 保存过滤条件
        file = os.path.join(folder, name)
        if os.path.exists(file):
            os.remove(file)  # clean up
        with open(file, "a", encoding="utf-8", newline='\n') as f:
            wr = csv.writer(f, dialect='excel', delimiter=sep)
            self.save_title(wr, sep)
            for bond in content_list:
                if math.isclose(float(bond["ZQNEW"]), 100, abs_tol=1e-6) or str(bond["LISTDATE"]) == '-':  # 排除未上市
                    continue
                if math.isclose(float(bond["YJL"]), 0.0, abs_tol=1e-6):  # 排除0溢价率
                    continue
                if float(bond["ZQNEW"]) > price:  # 排除高价格 -> 应该也要过滤掉价格为0的？
                    continue
                if float(bond["YJL"]) / 100 > rate:  # 排除高溢价率
                    continue
                self.save_item(wr, bond)
        print("保存成功: " + file)

    def save_focused_content(self, folder, name, content_list, code_list, sep=','):  # 保存关注代码
        file = os.path.join(folder, name)
        if os.path.exists(file):
            os.remove(file)  # clean up
        with open(file, "a", encoding="utf-8", newline='\n') as f:
            wr = csv.writer(f, dialect='excel', delimiter=sep)
            self.save_title(wr, sep)
            for bond in content_list:
                if bond["BONDCODE"] not in code_list:  # 排除不在关注列表中的记录
                    continue
                self.save_item(wr, bond)
        print("保存成功: " + file)

    def save_title(self, write, sep):  # 保存标题
        # file.write("\xEF\xBB\xBF\n")  # resolve encoding problems by Microsoft excel
        write.writerow(["债券代码_简称_申购代码", "发行规模（亿元）", "正股代码_简称", "正股价_转股价",
                        "转股价值", "债现价", "转股溢价率", "中签号发布日_中签率%", "上市日期"])

    def save_item(self, write, bond):  # 保存记录
        write.writerow([bond["BONDCODE"] + "_" + bond["SNAME"] + "_" + bond["CORRESCODE"], bond["AISSUEVOL"],
                        bond["SWAPSCODE"] + "_" + bond["SECURITYSHORTNAME"],
                        str(bond["ZGJ"]) + "_" + str(bond["SWAPPRICE"]),
                        bond["ZGJZGJJZ"], bond["ZQNEW"], str(bond["YJL"]) + "%",
                        bond["ZQHDATE"][:10] + "_" + str(bond["LUCKRATE"]), bond["LISTDATE"][:10]]);

    def run(self):  # 实现主要逻辑
        # 1.start_url
        url = self.kzz_url
        if self.date_desc is True:
            url = url + "&sr=-1"
        print("Requesting: " + url)
        # 2.发送请求,获取响应
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Mobile Safari/537.36", }
        get_response = requests.get(url, headers=headers)
        json_response = get_response.content.decode()  # print(json_response)
        # 3.提取数据
        bond_list, total = self.parse_content(json_response)  # kzz.json
        # 4.保存
        suffix = str(time.strftime("%Y%m%d", time.localtime()))  # 格式化成20160320形式
        target_folder = self.init_folder(suffix)
        self.save_content_list(target_folder, 'kzz_' + suffix + '.csv', bond_list)
        self.save_filtered_content(target_folder, 'kzz_' + suffix + '_filtered.csv', bond_list, self.price, self.rate,
                                   '\t')

        # 关注：
        mine = ['110059', '110063', '113531', '113540', '113545', '123036', '123041', '128075', '128089', '128092']
        mine.extend(['132018', '128070', '123028', '113537', '128068', '113535', '113026', '113532', '128062'])
        mine.extend(['110057', '113531', '128060', '127012', '123023', '110053', '113022', '113529', '128057', '113021',
                     '113528', '127006', '127005', '128036', '113019', '110043', '128034', '128034', '113018',
                     '128024'])
        self.save_focused_content(target_folder, 'kzz_' + suffix + '_history.csv', bond_list, mine, '\t')

if __name__ == '__main__':
    kzzSpider = KzzSpider('desc', 115, 0.15)
    kzzSpider.run()
