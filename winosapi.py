import os
import win32api
import win32con
import win32gui_struct
import win32gui
import os

Main = None


class SysTrayIcon(object):
    QUIT = 'QUIT'
    SPECIAL_ACTIONS = [QUIT]
    FIRST_ID = 1314

    def __init__(s,
                 icon,
                 hover_text,
                 menu_options,
                 on_quit=None,
                 default_menu_index=None,
                 window_class_name=None, ):
        s.icon = icon
        s.hover_text = hover_text
        s.on_quit = on_quit

        menu_options = menu_options + (('退出', None, s.QUIT),)
        s._next_action_id = s.FIRST_ID
        s.menu_actions_by_id = set()
        s.menu_options = s._add_ids_to_menu_options(list(menu_options))
        s.menu_actions_by_id = dict(s.menu_actions_by_id)
        del s._next_action_id

        s.default_menu_index = (default_menu_index or 0)
        s.window_class_name = window_class_name or "SysTrayIconPy"

        message_map = {win32gui.RegisterWindowMessage("TaskbarCreated"): s.refresh_icon,
                       win32con.WM_DESTROY: s.destroy,
                       win32con.WM_COMMAND: s.command,
                       win32con.WM_USER + 20: s.notify, }
        # 注册窗口类。
        window_class = win32gui.WNDCLASS()
        window_class.hInstance = win32gui.GetModuleHandle(None)
        window_class.lpszClassName = s.window_class_name
        window_class.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW;
        window_class.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        window_class.hbrBackground = win32con.COLOR_WINDOW
        window_class.lpfnWndProc = message_map  # 也可以指定wndproc.
        s.classAtom = win32gui.RegisterClass(window_class)

    def show_icon(s):
        # 创建窗口。
        hinst = win32gui.GetModuleHandle(None)
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        s.hwnd = win32gui.CreateWindow(s.classAtom,
                                       s.window_class_name,
                                       style,
                                       0,
                                       0,
                                       win32con.CW_USEDEFAULT,
                                       win32con.CW_USEDEFAULT,
                                       0,
                                       0,
                                       hinst,
                                       None)
        win32gui.UpdateWindow(s.hwnd)
        s.notify_id = None
        s.refresh_icon()

        win32gui.PumpMessages()

    def show_menu(s):
        menu = win32gui.CreatePopupMenu()
        s.create_menu(menu, s.menu_options)
        # win32gui.SetMenuDefaultItem(menu, 1000, 0)

        pos = win32gui.GetCursorPos()
        # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winui/menus_0hdi.asp
        win32gui.SetForegroundWindow(s.hwnd)
        win32gui.TrackPopupMenu(menu,
                                win32con.TPM_LEFTALIGN,
                                pos[0],
                                pos[1],
                                0,
                                s.hwnd,
                                None)
        win32gui.PostMessage(s.hwnd, win32con.WM_NULL, 0, 0)

    def destroy(s, hwnd, msg, wparam, lparam):
        if s.on_quit: s.on_quit(s)  # 运行传递的on_quit
        nid = (s.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)  # 退出托盘图标

    def notify(s, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONDBLCLK:  # 双击左键
            pass  # s.execute_menu_option(s.default_menu_index + s.FIRST_ID)
        elif lparam == win32con.WM_RBUTTONUP:  # 单击右键
            s.show_menu()
        elif lparam == win32con.WM_LBUTTONUP:  # 单击左键
            nid = (s.hwnd, 0)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
            win32gui.PostQuitMessage(0)  # 退出托盘图标
            if Main: Main.root.deiconify()
        return True

    def _add_ids_to_menu_options(s, menu_options):
        result = []
        for menu_option in menu_options:
            option_text, option_icon, option_action = menu_option
            if callable(option_action) or option_action in s.SPECIAL_ACTIONS:
                s.menu_actions_by_id.add((s._next_action_id, option_action))
                result.append(menu_option + (s._next_action_id,))
            else:
                result.append((option_text,
                               option_icon,
                               s._add_ids_to_menu_options(option_action),
                               s._next_action_id))
            s._next_action_id += 1
        return result

    def refresh_icon(s, **data):
        hinst = win32gui.GetModuleHandle(None)
        if os.path.isfile(s.icon):  # 尝试找到自定义图标
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hicon = win32gui.LoadImage(hinst,
                                       s.icon,
                                       win32con.IMAGE_ICON,
                                       0,
                                       0,
                                       icon_flags)
        else:  # 找不到图标文件 - 使用默认值
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        if s.notify_id:
            message = win32gui.NIM_MODIFY
        else:
            message = win32gui.NIM_ADD
        s.notify_id = (s.hwnd,
                       0,
                       win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                       win32con.WM_USER + 20,
                       hicon,
                       s.hover_text)
        win32gui.Shell_NotifyIcon(message, s.notify_id)

    def create_menu(s, menu, menu_options):
        for option_text, option_icon, option_action, option_id in menu_options[::-1]:
            if option_icon:
                option_icon = s.prep_menu_icon(option_icon)

            if option_id in s.menu_actions_by_id:
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                wID=option_id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
            else:
                submenu = win32gui.CreatePopupMenu()
                s.create_menu(submenu, option_action)
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                hSubMenu=submenu)
                win32gui.InsertMenuItem(menu, 0, 1, item)

    def prep_menu_icon(s, icon):
        # 首先加载图标。
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYSMICON)
        hicon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON, ico_x, ico_y, win32con.LR_LOADFROMFILE)

        hdcBitmap = win32gui.CreateCompatibleDC(0)
        hdcScreen = win32gui.GetDC(0)
        hbm = win32gui.CreateCompatibleBitmap(hdcScreen, ico_x, ico_y)
        hbmOld = win32gui.SelectObject(hdcBitmap, hbm)
        # 填满背景。
        brush = win32gui.GetSysColorBrush(win32con.COLOR_MENU)
        win32gui.FillRect(hdcBitmap, (0, 0, 16, 16), brush)
        # "GetSysColorBrush返回缓存的画笔而不是分配新的画笔。"
        #  - 暗示没有DeleteObject
        # 画出图标
        win32gui.DrawIconEx(hdcBitmap, 0, 0, hicon, ico_x, ico_y, 0, 0, win32con.DI_NORMAL)
        win32gui.SelectObject(hdcBitmap, hbmOld)
        win32gui.DeleteDC(hdcBitmap)

        return hbm

    def command(s, hwnd, msg, wparam, lparam):
        id = win32gui.LOWORD(wparam)
        s.execute_menu_option(id)

    def execute_menu_option(s, id):
        menu_action = s.menu_actions_by_id[id]
        if menu_action == s.QUIT:
            win32gui.DestroyWindow(s.hwnd)
        else:
            menu_action(s)


import tkinter as tk
root = tk.Tk()
labelText = tk.StringVar()

class _Main:

    def main(s):
        #########################      tkinter界面设定      #####################################


        from school import inter, getuser,init_timer_loop

        var1 = tk.IntVar()
        var2 = tk.StringVar()
        var3 = tk.StringVar()
        var4 = tk.IntVar()

        my_path = 'C:\\Users\\' + getuser() + '\\Documents\\school'
        my_ts = 'C:\\Users\\' + getuser() + '\\Documents\\school\\my_user.txt'
        global text

        tk.Label(root, text="请输入学号").grid(row=0, column=0)
        tk.Label(root, text="请输入密码").grid(row=1, column=0)

        e1 = tk.Entry(root, textvariable=var2)
        e1.grid(row=0, column=1, padx=10, pady=5)
        e2 = tk.Entry(root, show="*", textvariable=var3)
        e2.grid(row=1, column=1, padx=10, pady=5)
        c1 = tk.Checkbutton(root, text='学生账号', variable=var1, onvalue=1, offvalue=0).place(x=170, y=60, anchor='nw')
        c2 = tk.Checkbutton(root, text='启动监听', command=lambda: init_timer_loop(), onvalue=1, offvalue=0).place(x=170, y=80, anchor='nw')
        try:
            with open(my_ts) as fp:
                user = fp.readlines()
                fp.close()
            var2.set(user[0])
            var3.set(user[1])
        except:
            pass


        # net_statu = ["网络丢失","网络已连接"]

        tk.Label(root,textvariable=labelText).place(x=100,y=70)



        tk.Button(root, text="确定", width=10, command=lambda: inter(var2.get(), var3.get(), var1.get())).grid(row=3,
                                                                                                          column=0,

                                                                                                          padx=10,
                                                                                                          pady=5)



        ###########################     开始托盘程序嵌入     #####################################
        s.root = root
        icons = os.getcwd() + r'\ico.ico'
        print(icons)
        hover_text = "智能对话小助手"  # 悬浮于图标上方时的提示
        menu_options = ()
        s.sysTrayIcon = SysTrayIcon(icons, hover_text, menu_options, on_quit=s.exit, default_menu_index=1)

        s.root.bind("<Unmap>", lambda event: s.Unmap() if s.root.state() == 'iconic' else False)
        s.root.protocol('WM_DELETE_WINDOW', s.exit)
        s.root.resizable(0, 0)
        s.root.mainloop()



    def switch_icon(s, _sysTrayIcon, icons='D:\\2.ico'):
        _sysTrayIcon.icon = icons
        _sysTrayIcon.refresh_icon()
        # 点击右键菜单项目会传递SysTrayIcon自身给引用的函数，所以这里的_sysTrayIcon = s.sysTrayIcon


    def Unmap(s):
        s.root.withdraw()
        s.sysTrayIcon.show_icon()

    def exit(s, _sysTrayIcon=None):
        s.root.destroy()
        print('exit...')


if __name__ == '__main__':
    Main = _Main()
    Main.main()