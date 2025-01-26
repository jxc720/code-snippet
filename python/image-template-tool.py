import os
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import subprocess

from util.ai_util import generate_variable_name # 将中文名翻译成变量名的工具
from util.open_cv_util import template_matching # 模板匹配方法


ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.join(ROOT_PATH, "data", "screenshots")
INPUT_PATH = os.path.join(ROOT_PATH, "data", "input")

@dataclass
class ImageElementInfo:
    name: str
    element_variable_name: str
    file_name: str
    rel_element_file: str
    abs_element_file: str
    image: Image.Image


def screenshot():
    screenshot_file = os.path.join(SCREENSHOTS_DIR, 'screenshot.png')
    # 使用adb获取截图
    subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screenshot.png"])
    subprocess.run(["adb", "pull", "/sdcard/screenshot.png", screenshot_file])
    return screenshot_file


class ImageLabelerApp:
    def __init__(self, parent):

        # 创建左侧框架
        left_frame = tk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True, padx=10, pady=10)
        # 创建右侧框架
        right_frame = tk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.theme_use("clam")
        # 左侧大图展示（使用Canvas）
        self.canvas_width = 470
        self.canvas_height = 1000
        self.canvas = tk.Canvas(left_frame, width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack(padx=10, pady=10)

        # 左下侧更新截图按钮
        self.capture_button = ttk.Button(left_frame, text="更新截图", command=self.capture_screenshot)
        self.capture_button.pack(padx=10, pady=10)

        # 右上侧小图预览
        self.preview_width = 300  # 预览图宽度
        self.preview_height = 300  # 预览图高度
        self.preview_image_label = ttk.Label(right_frame)
        self.preview_image_label.grid(row=0, column=0, padx=10, pady=10)

        # 右侧文本输入框
        element_name_input_frame = tk.Frame(right_frame)
        element_name_input_frame.grid(row=1, column=0, padx=10, pady=10)

        self.element_name_input_label = tk.Label(element_name_input_frame, text="元素名:")
        self.element_name_input_label.pack(side=tk.LEFT, padx=0, pady=10)
        self.element_name_input = tk.Entry(element_name_input_frame, width=30)
        self.element_name_input.pack(side=tk.LEFT, padx=0, pady=10)

        # 右侧操作按钮
        self.save_button = tk.Button(element_name_input_frame, text="保存元素", command=self.save_cropped_image)
        self.save_button.pack(side=tk.LEFT, padx=0, pady=10)

        # 右侧列表
        self.list_frame = tk.Frame(right_frame)
        self.list_frame.grid(row=3, column=0, padx=10, pady=10)

        # 初始化变量
        self.image = None  # 原始截图
        self.cropped_image = None  # 裁剪原图
        self.scaled_image = None  # 缩放后的截图
        self.tk_image = None  # 用于显示的缩放截图
        self.preview_image = None  # 预览图
        self.tk_preview_image = None  # 用于显示的预览图
        self.scale_factor = 1.0  # 缩放比例

        self.rect_id = None  # 矩形框的ID
        self.start_x = None  # 框选起始X坐标
        self.start_y = None  # 框选起始Y坐标
        self.end_x = None  # 框选结束X坐标
        self.end_y = None  # 框选结束Y坐标

        self.cropped_image_name = None  # 裁剪图片文件名

        self.element_list: list[ImageElementInfo] = []  # 已录入元素

        self.capture_screenshot()

    def capture_screenshot(self):
        screenshot_file = screenshot()
        # 加载截图
        self.image = Image.open(screenshot_file)
        self.update_canvas()

    def update_canvas(self):
        # 缩放截图以适应界面
        self.scale_factor = min(self.canvas_width / self.image.width, self.canvas_height / self.image.height)
        self.scaled_image = self.image.resize(
            (int(self.image.width * self.scale_factor), int(self.image.height * self.scale_factor)),
            Image.Resampling.LANCZOS
        )

        # 显示缩放后的截图
        # 左侧大图展示（使用Canvas）
        self.canvas.config(width=self.scaled_image.width, height=self.scaled_image.height)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        # 截图加载完成后，自动启用框选功能
        self.enable_selection()

    def enable_selection(self):
        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def on_button_press(self, event):
        # 记录鼠标按下的位置
        self.start_x = event.x
        self.start_y = event.y

        # 如果已经有矩形框，先删除
        if self.rect_id:
            self.canvas.delete(self.rect_id)

        # 创建新的矩形框
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2
        )

    def on_mouse_drag(self, event):
        # 更新矩形框的大小
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        # 记录鼠标释放的位置
        self.end_x = event.x
        self.end_y = event.y
        print(f"开始坐标: ({self.start_x}, {self.start_y}), 结束坐标: ({self.end_x}, {self.end_y})")

        # 如果区域太小则不框选
        if min(abs(self.end_x - self.start_x), abs(self.end_y - self.start_y)) < 20:
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            return

        # 裁剪图像并显示在预览框中
        if self.image:
            # 裁剪原始图像
            self.cropped_image = self.image.crop(
                self.get_original_box()
            )

            # 缩放预览图以适应预览框
            preview_scale_factor = min(
                self.preview_width / self.cropped_image.width,
                self.preview_height / self.cropped_image.height
            )
            preview_image = self.cropped_image.resize(
                (
                    int(self.cropped_image.width * preview_scale_factor),
                    int(self.cropped_image.height * preview_scale_factor)
                ),
                Image.Resampling.LANCZOS
            )

            # 显示预览图
            self.tk_preview_image = ImageTk.PhotoImage(preview_image)
            # noinspection PyTypeChecker
            self.preview_image_label.config(image=self.tk_preview_image)

    # 计算原始图像中的坐标
    def get_original_box(self):
        left = int(min(self.start_x, self.end_x) / self.scale_factor)
        top = int(min(self.start_y, self.end_y) / self.scale_factor)
        right = int(max(self.end_x, self.start_x) / self.scale_factor)
        bottom = int(max(self.end_y, self.start_y) / self.scale_factor)
        return left, top, right, bottom

    def save_cropped_image(self):
        if self.image is None or self.start_x is None:
            return

        # 元素名校验
        element_name = self.element_name_input.get()
        if not element_name.strip():  # 检查输入是否为空
            # 弹出提示框
            messagebox.showwarning("提示", "元素名不能为空！")
            return

        # 时间格式化
        now = datetime.now()
        # todo 这里要使用你自己项目里的获取变量名的方法，推荐调用gpt
        # element_variable_name = generate_variable_name(element_name)
        element_variable_name = 'button'
        time_str = now.strftime("%H%M%S")
        element_file_name = f"{time_str}_{element_variable_name}.png"

        # 路径
        year = now.strftime("%Y")
        month = now.strftime("%m")
        # 相对路径
        rel_element_path = os.path.join('element_image', year, month)
        abs_element_path = os.path.join(INPUT_PATH, rel_element_path)
        if not os.path.exists(abs_element_path):
            os.makedirs(abs_element_path)
        rel_element_file = os.path.join(rel_element_path, element_file_name)
        abs_element_file = os.path.join(abs_element_path, element_file_name)

        # 裁剪原始图像
        cropped_image = self.image.crop(
            self.get_original_box()
        )
        # 保存裁剪后的图像
        cropped_image.save(os.path.join(abs_element_path, element_file_name))

        # 保存元素信息
        element_info = ImageElementInfo(name=element_name, element_variable_name=element_variable_name,
                                        file_name=element_file_name, rel_element_file=rel_element_file,
                                        abs_element_file=abs_element_file, image=cropped_image)
        self.element_list.append(element_info)
        self.update_list()
        # 上传到服务器
        # file_url = upload_file(cropped_image_file)

    # 更新列表显示的函数
    def update_list(self):
        # 清空当前列表
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        # 重新渲染列表
        for index, item in enumerate(self.element_list):
            # 创建每行的框架
            row_frame = tk.Frame(self.list_frame)
            row_frame.pack(fill=tk.X, pady=2)
            # 显示文本
            label = tk.Label(row_frame, text=f'{item.name} {item.element_variable_name}', anchor="w")
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            # 复制按钮
            copy_button = tk.Button(row_frame, text="复制代码", command=lambda i=index: self.copy_element_code(i))
            copy_button.pack(side=tk.RIGHT)
            # 删除按钮
            copy_button = tk.Button(row_frame, text="删除文件", command=lambda i=index: self.delete_element(i))
            copy_button.pack(side=tk.RIGHT)
            # 验证按钮
            copy_button = tk.Button(row_frame, text="验证", command=lambda i=index: self.verify_element(i))
            copy_button.pack(side=tk.RIGHT)

    # 复制指定行的函数
    def copy_element_code(self, index):
        item = self.element_list[index]
        # todo 这里改成你项目里的写法
        element_code_str = f'{item.element_variable_name} = click_image(Image.open("{item.abs_element_file}"))'
        root.clipboard_clear()
        root.clipboard_append(element_code_str)

    # 删除指定行的函数
    def delete_element(self, index):
        # 删除文件
        item = self.element_list[index]
        if os.path.exists(item.abs_element_file):
            os.remove(item.abs_element_file)
        # 从列表中移除
        self.element_list.pop(index)
        # 更新列表显示
        self.update_list()

    # 验证指定行的函数
    def verify_element(self, index):
        item = self.element_list[index]
        # todo 这里要使用你自己项目里的图片模板匹配方法
        image_result_path = template_matching(screenshot(), item.abs_element_file)[1]
        if image_result_path is None:
            # 弹出提示框
            messagebox.showwarning("提示", "未匹配到元素")
            return
        self.image = Image.open(image_result_path)
        self.update_canvas()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("模板匹配录入工具")
    # 创建主框架
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)
    app = ImageLabelerApp(main_frame)
    root.mainloop()
