#!/usr/bin/python

class FormButton:
    def __init__(self, **kw):
        self.action = ''
        self.button_text = ''
        self.button_name = ''
        self.method = "POST"
        self.text_before_button = ''
        self.post_vars = []
        for k in kw.keys():
            if self.__dict__.has_key(k):
                self.__dict__[k] = kw[k]

    def __str__(self):
        s = '<form action="%s" method="%s">\n' % (self.action, self.method)
        for p in self.post_vars:
            s += ' <input type="%s" name="%s" value="%s">\n' % (
                p['ftype'], p['fname'], p['fvalue'])
        s += ' %s <input class="button" type="SUBMIT" name=%s value="%s">\n' % (
            self.text_before_button, self.button_name, self.button_text)
        s += '</form>'
        return s
    def add_field(self, ftype, fname, fvalue):
        self.post_vars.append({'ftype' :ftype, 'fname': fname, 
                               'fvalue': fvalue})
    def render(self):
        return str(self)

class ULList:
    def __init__(self):
        self.items = []
    def __str__(self):
        return self.render()
    def render(self):
        txt = "<UL>\n"
        for i in self.items:
            txt += "<LI>%s</LI>\n" % i
        txt += "</UL>\n"
        return txt


class Menu:
    def __init__(self):
        self.menu = {}
        self.menu['order'] = []
    def __str__(self):
        return self.render()
    def add_title(self, title, url=''):
        self.menu[title] = {'url' : url}
        self.menu[title]['items'] = {}
        self.menu['order'].append(title)
        self.menu[title]['order'] = []
    def add_item(self, title, item, url='#', description=''):
        self.menu[title]['items'][item] = {'url' : url,
                                           'description' : description }
        self.menu[title]['order'].append(item)
    def render(self):
        msg = '  <div class="menu">\n'
        msg += '    <ul>\n'
        for t in self.menu['order']:
            msg += '     <li>\n'
            msg += '     <a href="%s">%s</a>\n' % (self.menu[t]['url'], t)
            if self.menu[t]['items']:
                msg += '      <ul>\n'
                for i in self.menu[t]['order']:
                    msg += '      <li><a href="%s" title="%s">%s</a></li>\n' % (
                        self.menu[t]['items'][i]['url'],
                        self.menu[t]['items'][i]['description'], i)
                msg += '      </ul>\n'
            msg+='     </li>\n'
        msg += '    </ul>\n'
        msg += '  </div>\n'
        return msg

class Table(object):
    def __init__(self, **kw):
        self.border = 1
        self.width = 400
        self.columns = 0
        self.cellspacing = 0
        self.cellpadding = 0
        self.caption = ''
        self.th = []
        self.td = []
        self.body = ''
        self.pretext = ''
        for k in kw.keys():
            if self.__dict__.has_key(k):
                self.__dict__[k] = kw[k]

    def __str__(self):
        s = '<table border=%s cellpadding=%s cellspacing=%s width=%s>\n'\
          % (self.border, self.cellpadding, self.cellspacing, self.width)
        if self.caption:
            s += ' <caption>%s</caption>\n' % self.caption
        if self.th:
            s += ' <tr>\n'
            for x in self.th:
                s += '  <th'
                if x.color or x.bgcolor:
                    s += ' style="'
                    if x.color:
                        s += 'color:%s ' % x.color
                    if x.bgcolor:
                        s += 'bgcolor:%s' % x.bgcolor
                s += '>%s</th>\n' % x.text
            s += ' </tr>\n'
        for y in self.td:
            s += ' <tr>\n'
            for x in y:
                s += '  <td'
                if x.color or x.bgcolor or x.align:
                    s += ' style="'
                    if x.color:
                        s += 'color:%s; ' % x.color
                    if x.bgcolor:
                        s += 'background-color:%s;' % x.bgcolor
                    if x.align:
                        s += 'text-align:%s;' % x.align
                    s += '"'
                s += '>%s</td>\n' % x.text
            s += '</tr>\n'
        s += '</table>\n'

        return s



    def header(self, fields):
        if type(fields) != list:
            raise "Value must be a list"
        self.columns = len(fields)
        for x in fields:
            if type(x) != TableField:
                o = TableField(text = x)
            else:
                o = x
            self.th.append(o)

    def row(self, fields):
        if type(fields) != list:
            raise "Value must be a list"
        if len(fields) != self.columns:
            raise Exception, "Not enough fields specified. Expected %s and got %s" % (
                             self.columns, len(fields))
        temp = []
        for x in fields:
            if type(x) != TableField:
                o = TableField(text = x)
            else:
                o = x
            temp.append(o)
        self.td.append(temp)

    def render(self):
        return self.__str__()



class TableField(object):
    def __init__(self, **kw):
        self.text = ''
        self.color= ''
        self.bgcolor = ''
        self.align = ''
        for k in kw.keys():
            if self.__dict__.has_key(k):
                self.__dict__[k] = kw[k]



def link(txt, link, br=''):
    if br:
        br="<br>"
    else:
        br=""
    return ' <a href = "%s">%s</a>%s' % (link, txt, br)
