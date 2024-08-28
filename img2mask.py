import  wx
import os
import pandas as pd
from datetime import datetime
import csv
import base64
import threading


def split_string_by_21(s):
    return [s[i:i + 18] for i in range(0, len(s), 18)]


def base64_encode(data):
    if isinstance(data, str):
        data = data.encode()
    b = base64.b64encode(data).decode()
    b = b.replace('+', '-').replace('/', '_')
    return b.rstrip('=')


def get_url(url, time, watermark):
    pic_url = url
    pic_time = time
    address = watermark
    address_list = split_string_by_21(address)
    a = base64_encode('地 址：' + str(address_list[0]))
    a1 = base64_encode(address_list[1]) if len(address_list) >= 2 else ''

    try:
        time_pic = datetime.strptime(pic_time.replace('/', '-'), '%Y-%m-%d %H:%M:%S')
        time = time_pic.strftime('%H:%M:%S')
        date = time_pic.strftime('%Y-%m-%d')
    except Exception as e:
        time = datetime.now().strftime('%H:%M:%S')
        date = datetime.now().strftime('%Y-%m-%d')

    time = base64_encode(time)
    date = base64_encode('日 期：' + date)

    watermark_parts = [
        '?x-oss-process=image/resize,w_1366',
        f'/watermark,color_FFFFFF,size_70,shadow_100,x_30,y_175,g_sw,text_{time}',
        f'/watermark,color_FFFFFF,size_40,shadow_100,x_30,y_120,g_sw,text_{date}',
        f'/watermark,color_FFFFFF,size_40,shadow_100,x_25,y_75,g_sw,text_{a}'
    ]

    if a1:
        watermark_parts.append(f'/watermark,color_FFFFFF,size_40,shadow_100,x_190,y_30,g_sw,text_{a1}')

    if pic_url.startswith(('http://', 'https://')):
        return pic_url + ''.join(watermark_parts)
    return pic_url


class ImageProcessorFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='图片水印处理工具')
        panel = wx.Panel(self)

        # 创建控件
        self.file_picker = wx.FilePickerCtrl(panel, message="选择数据文件")
        self.dir_picker = wx.DirPickerCtrl(panel, message="选择保存路径")
        self.time_combo = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        self.watermark_combo = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        self.start_button = wx.Button(panel, label="开始处理")
        self.status_text = wx.StaticText(panel, label="请选择数据文件和保存路径")
        self.progress_bar = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)

        # 布局
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(panel, label="数据文件:"), 0, wx.ALL, 5)
        sizer.Add(self.file_picker, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, label="保存路径:"), 0, wx.ALL, 5)
        sizer.Add(self.dir_picker, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, label="时间列:"), 0, wx.ALL, 5)
        sizer.Add(self.time_combo, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, label="水印列:"), 0, wx.ALL, 5)
        sizer.Add(self.watermark_combo, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.start_button, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.status_text, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)

        # 绑定事件
        self.file_picker.Bind(wx.EVT_FILEPICKER_CHANGED, self.on_file_selected)
        self.start_button.Bind(wx.EVT_BUTTON, self.on_start)

        self.SetSize((500, 400))
        self.Centre()

    def on_file_selected(self, event):
        file_path = self.file_picker.GetPath()
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path, nrows=0)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=0)
        else:
            wx.MessageBox("不支持的文件格式", "错误", wx.OK | wx.ICON_ERROR)
            return

        columns = list(df.columns)
        self.time_combo.SetItems(columns)
        self.watermark_combo.SetItems(columns)

        time_col = next((col for col in columns if '时间' in col), None)
        if time_col:
            self.time_combo.SetStringSelection(time_col)

        watermark_col = next((col for col in columns if '水印' in col or '地址' in col), None)
        if watermark_col:
            self.watermark_combo.SetStringSelection(watermark_col)

    def on_start(self, event):
        file_path = self.file_picker.GetPath()
        save_path = self.dir_picker.GetPath()
        time_col = self.time_combo.GetStringSelection()
        watermark_col = self.watermark_combo.GetStringSelection()

        if not all([file_path, save_path, time_col, watermark_col]):
            wx.MessageBox("请确保所有选项都已选择", "错误", wx.OK | wx.ICON_ERROR)
            return

        self.start_button.Disable()
        thread = threading.Thread(target=self.process_file, args=(file_path, save_path, time_col, watermark_col))
        thread.start()

    def process_file(self, file_path, save_path, time_col, watermark_col):
        try:
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                wx.CallAfter(self.status_text.SetLabel, "不支持的文件格式")
                return

            total_rows = len(df)
            wx.CallAfter(self.progress_bar.SetRange, total_rows)

            output_file = os.path.join(save_path, os.path.splitext(os.path.basename(file_path))[0] + '_处理后.csv')

            with open(output_file, 'w', encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(df.columns)

                for index, row in df.iterrows():
                    time = row[time_col]
                    watermark = row[watermark_col]
                    new_row = []
                    for col, value in row.items():
                        if isinstance(value, str) and '//' in value and value.lower().endswith('.jpg'):
                            url = value.split(';')[0]
                            new_url = get_url(url, time, watermark)
                            new_row.append(new_url)
                        else:
                            new_row.append(value)
                    writer.writerow(new_row)

                    wx.CallAfter(self.progress_bar.SetValue, index + 1)

            wx.CallAfter(self.status_text.SetLabel, f"处理完成，结果保存至: {output_file}")
        except Exception as e:
            wx.CallAfter(self.status_text.SetLabel, f"处理过程中出错: {str(e)}")
        finally:
            wx.CallAfter(self.start_button.Enable)


if __name__ == '__main__':
    app = wx.App()
    frame = ImageProcessorFrame()
    frame.Show()
    app.MainLoop()
