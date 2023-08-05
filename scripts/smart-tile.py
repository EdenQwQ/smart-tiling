import subprocess
import os
import operator
import argparse
from json import loads

class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def move(self, dx, dy):
        return Position(self.x + dx, self.y + dy)

class Size:
    def __init__(self, width, height):
        self.w = width
        self.h = height
class Window:
    def __init__(self, address, pos, size):
        self.address = address
        self.pos = pos
        self.size = size
        self.area = size.w * size.h
    def topleft(self):
        return self.pos
    def topright(self):
        return self.pos.move(self.size.w, 0)
    def bottomleft(self):
        return self.pos.move(0, self.size.h)
    def bottomright(self):
        return self.pos.move(self.size.w, self.size.h)
    def is_overlapping(self, other):
        return not (self.pos.x >= other.topright().x or self.topright().x <= other.pos.x or self.pos.y >= other.bottomleft().y or self.bottomleft().y <= other.pos.y)

def find_spare_space(existing_windows, newwindow_size):
    spare_space_pos = []
    spare_space_size = []
    area_in_canvas = []
    nodes = []
    xs = []
    ys = []
    for window in existing_windows:
        nodes.append(window.topright())
        nodes.append(window.bottomleft())
        nodes.append(window.bottomright())
        xs.append(window.pos.x)
        ys.append(window.pos.y)
    nodes.append(Position(canvas_size.w, canvas_size.h))
    xs.sort()
    ys.sort()
    for node in nodes:
        if node == Position(canvas_size.w, canvas_size.h):
            continue
        newwindow = Window(-1, node, newwindow_size)
        have_overlap = False
        for window in existing_windows:
            if newwindow.is_overlapping(window):
                have_overlap = True
                break
        if not have_overlap:
            spare_space_pos.append(node)
            if node.x > canvas_size.w or node.y > canvas_size.h:
                area_in_canvas.append(0)
                spare_space_size.append(None)
                continue
            if node.x + newwindow_size.w > canvas_size.w and node.y + newwindow_size.h > canvas_size.h:
                area_in_canvas.append((canvas_size.w - node.x) * (canvas_size.h - node.y))
                spare_space_size.append(None)
                continue
            if node.x + newwindow_size.w > canvas_size.w:
                area_in_canvas.append((canvas_size.w - node.x) * newwindow_size.h)
                spare_space_size.append(None)
                continue
            if node.y + newwindow_size.h > canvas_size.h:
                area_in_canvas.append((canvas_size.h - node.y) * newwindow_size.w)
                spare_space_size.append(None)
                continue
            area_in_canvas.append(-1)
            width = 0
            nodes_right = list(filter(lambda n: n.x >= node.x, nodes))
            nodes_right.sort(key=operator.attrgetter('x'), reverse=True)
            for node_right in nodes_right:
                newwindow = Window(-1, node, Size(node_right.x - node.x, 0))
                have_overlap = False
                for window in existing_windows:
                    if newwindow.is_overlapping(window):
                        have_overlap = True
                        break
                if not have_overlap:
                    width = node_right.x - node.x
                    break
            height = 0
            nodes_bottom = list(filter(lambda n: n.y >= node.y, nodes))
            nodes_bottom.sort(key=operator.attrgetter('y'), reverse=True)
            for node_bottom in nodes_bottom:
                newwindow = Window(-1, node, Size(0, node_bottom.y - node.y))
                have_overlap = False
                for window in existing_windows:
                    if newwindow.is_overlapping(window):
                        have_overlap = True
                        break
                if not have_overlap:
                    height = node_bottom.y - node.y
                    break
            spare_space_size.append(Size(width, height))
    return spare_space_pos, spare_space_size, area_in_canvas

def choose_best_spare_space(spare_space_pos, spare_space_size, area_in_canvas):
    if -1 not in area_in_canvas:
        return spare_space_pos[area_in_canvas.index(max(area_in_canvas))]
    min_area = 1024000
    best_pos = spare_space_pos[0]
    for i in range(len(spare_space_size)):
        size = spare_space_size[i]
        if size == None:
            continue
        area = size.w * size.h
        if area < min_area:
            best_pos = spare_space_pos[i]
    return best_pos

def arrange_windows(windows):
    if len(windows) == 0:
        return
    if len(windows) == 1:
        center_pos = Position(canvas_pos.x + canvas_size.w / 2 - windows[0].size.w / 2, canvas_pos.y + canvas_size.h / 2 - windows[0].size.h / 2)
        move_window_to_pos(windows[0].address, center_pos)
        return

    windows.sort(key = operator.attrgetter('area'), reverse=True)

    if priors:
        for prior in priors:
            if any((prior_window := window).address == prior for window in windows):
                windows.pop(windows.index(prior_window))
                windows.insert(0, prior_window)

    windows[0].pos = Position(0, 0)
    arranged_windows = [windows[0]]
    right = windows[0].size.w
    bottom = windows[0].size.h
    for window in windows:
        if window.address == windows[0].address:
            continue
        spare_space_pos, spare_space_size, area_in_canvas = find_spare_space(arranged_windows, window.size)
        best_pos = choose_best_spare_space(spare_space_pos, spare_space_size, area_in_canvas)
        window.pos = best_pos
        arranged_windows.append(window)
        if window.bottomright().x > right:
            right = window.bottomright().x
        if window.bottomright().y > bottom:
            bottom = window.bottomright().y
    dx = canvas_pos.x
    dy = canvas_pos.y
    if right <= canvas_size.w:
        dx += (canvas_size.w - right) / 2
    if bottom <= canvas_size.h:
        dy += (canvas_size.h - bottom) / 2
    for window in arranged_windows:
        move_window_to_pos(window.address, Position(window.pos.x + dx, window.pos.y + dy))

def get_hyprctl_output_json(arguments):
    return loads(subprocess.run(['hyprctl', '-j', arguments], stdout = subprocess.PIPE).stdout)

def move_window_to_pos(windowaddress, pos):
    x = int(pos.x) + gap + border
    y = int(pos.y) + gap + border
    if x < 0 and y < 0:
        os.system(f'hyprctl dispatch movewindowpixel exact \'0 {y}\',address:{windowaddress}')
        os.system(f'hyprctl dispatch movewindowpixel {x} 0,address:{windowaddress}')
        return
    if x < 0:
        command = f'hyprctl dispatch movewindowpixel exact {x} {y},address:{windowaddress}'
    else:
        command = f'hyprctl dispatch movewindowpixel exact \'{x} {y}\',address:{windowaddress}'
    print(command)
    os.system(command)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Arrange windows in a smart way', allow_abbrev = False)
    parser.add_argument('workspaces', type = str, nargs = '*', help = 'workspaces to be tiled')
    parser.add_argument('--gap', type = int, nargs = '?', help = 'outer gap of a window', default = 5)
    parser.add_argument('--border', type = int, nargs = '?', help = 'border size of a window', default = 4)
    parser.add_argument('--canvas_pos', type = str, nargs = '?', help = 'position of the canvas, format: x,y')
    parser.add_argument('--canvas_size', type = str, nargs = '?', help = 'size of the canvas, format: w,h')
    parser.add_argument('--prior', type = str, nargs = '*', help = 'specify windows that should be priorly tiled')

    args = parser.parse_args()

    workspace_ids = args.workspaces

    priors = []
    if args.prior:
        for prior in args.prior:
            if prior[:1] != '0x':
                prior = '0x' + prior
            priors.insert(0, prior)

    gap = args.gap
    border = args.border
    if args.canvas_pos == None:
        canvas_pos = Position(5, 43)
    else:
        canvas_pos = Position(*map(int, args.canvas_pos.strip('\'').split(',')))
    if args.canvas_size == None:
        canvas_size = Size(1270, 753)
    else:
        canvas_size = Size(*map(int, args.canvas_size.strip('\'').split(',')))

    clients = get_hyprctl_output_json('clients')

    if workspace_ids == []:
        active_workspace = get_hyprctl_output_json('activeworkspace')
        workspace_ids = [active_workspace['id']]

    if workspace_ids[0] == 'all':
        workspace_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    for workspace_id in workspace_ids:
        clients_in_workspace = list(filter(lambda client: client['workspace']['id'] == int(workspace_id), clients))

        windows = []
        for client in clients_in_workspace:
            windows.append(Window(client['address'], Position(client['at'][0] - gap - border, client['at'][1] - gap - border), Size(client['size'][0] + 2 * (gap + border), client['size'][1] + 2 * (gap + border))))

        arrange_windows(windows)
