import subprocess
from cola import resources
from cola import qtutils
from cola.compat import set
    def __init__(self, parent):
        self._model = GitRefModel(parent)
        self.setModel(self._model)
        self.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._model.dispose()
class GitRefLineEdit(QtGui.QLineEdit):
        QtGui.QLineEdit.__init__(self, parent)
        self.refcompleter = GitRefCompleter(self)
        self.setCompleter(self.refcompleter)

class GitRefModel(QtGui.QStandardItemModel):
    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.cmodel = cola.model()
        msg = self.cmodel.message_updated
        self.cmodel.add_message_observer(msg, self.update_matches)
        self.update_matches()
        self.cmodel.remove_observer(self.update_matches)
    def update_matches(self):
        model = self.cmodel
        matches = model.local_branches + model.remote_branches + model.tags
        QStandardItem = QtGui.QStandardItem
        self.clear()
        for match in matches:
            item = QStandardItem()
            item.setIcon(qtutils.git_icon())
            item.setText(match)
            self.appendRow(item)

class GitLogCompletionModel(QtGui.QStandardItemModel):
    def __init__(self, parent):
        self.matched_text = None
        QtGui.QStandardItemModel.__init__(self, parent)
        self.cmodel = cola.model()

    def lower_cmp(self, a, b):
        return cmp(a.replace('.','').lower(), b.replace('.','').lower())

    def update_matches(self, case_sensitive):
        QStandardItem = QtGui.QStandardItem
        file_list = self.cmodel.everything()
        files = set(file_list)
        files_and_dirs = utils.add_parents(set(files))
        dirs = files_and_dirs.difference(files)

        file_icon = qtutils.file_icon()
        dir_icon = qtutils.dir_icon()
        git_icon = qtutils.git_icon()

        model = self.cmodel
        refs = model.local_branches + model.remote_branches + model.tags
        matched_text = self.matched_text

        if matched_text:
            if case_sensitive:
                matched_refs = [r for r in refs if matched_text in r]
            else:
                matched_refs = [r for r in refs
                                    if matched_text.lower() in r.lower()]
        else:
            matched_refs = refs

        matched_refs.sort(cmp=self.lower_cmp)

        if matched_text:
            if case_sensitive:
                matched_paths = [f for f in files_and_dirs
                                        if matched_text in f]
            else:
                matched_paths = [f for f in files_and_dirs
                                    if matched_text.lower() in f.lower()]
        else:
            matched_paths = list(files_and_dirs)

        matched_paths.sort(cmp=self.lower_cmp)

        items = []

        for ref in matched_refs:
            item = QStandardItem()
            item.setText(ref)
            item.setIcon(git_icon)
            items.append(item)

        if matched_paths and (not matched_text or matched_text in '--'):
            item = QStandardItem()
            item.setText('--')
            item.setIcon(file_icon)
            items.append(item)

        for match in matched_paths:
            item = QStandardItem()
            item.setText(match)
            if match in dirs:
                item.setIcon(dir_icon)
            else:
                item.setIcon(file_icon)
            items.append(item)

        self.clear()
        for item in items:
            self.appendRow(item)

    def set_match_text(self, text, case_sensitive):
        self.matched_text = text
        self.update_matches(case_sensitive)


class GitLogLineEdit(QtGui.QLineEdit):
        # used to hide the completion popup after a drag-select
        self._drag = 0

        self._model = GitLogCompletionModel(self)
        self._delegate = HighlightCompletionDelegate(self)

        self._completer = QtGui.QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setModel(self._model)
        self._completer.setCompletionMode(
                QtGui.QCompleter.UnfilteredPopupCompletion)
        self._completer.popup().setItemDelegate(self._delegate)

        self.connect(self._completer, SIGNAL('activated(QString)'),
                     self._complete)
        self.connect(self, SIGNAL('textChanged(QString)'), self._text_changed)
        self._keys_to_ignore = set([QtCore.Qt.Key_Enter,
                                    QtCore.Qt.Key_Return,
                                    QtCore.Qt.Key_Escape])

    def is_case_sensitive(self, text):
        return bool([char for char in text if char.isupper()])

    def _text_changed(self, text):
        text = self.last_word()
        case_sensitive = self.is_case_sensitive(text)
        if case_sensitive:
            self._completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        else:
            self._completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._delegate.set_highlight_text(text, case_sensitive)
        self._model.set_match_text(text, case_sensitive)

    def update_matches(self):
        text = self.last_word()
        case_sensitive = self.is_case_sensitive(text)
        self._model.update_matches(case_sensitive)

    def _complete(self, completion):
        """
        This is the event handler for the QCompleter.activated(QString) signal,
        it is called when the user selects an item in the completer popup.
        """
        if not completion:
            return
        words = self.words()
        if words:
            words.pop()
        words.append(unicode(completion))
        self.setText(subprocess.list2cmdline(words))
        self.emit(SIGNAL('ref_changed'))

    def words(self):
        return utils.shell_usplit(unicode(self.text()))

    def last_word(self):
        words = self.words()
        if not words:
            return unicode(self.text())
        if not words[-1]:
            return u''
        return words[-1]

    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if (event.key() == QtCore.Qt.Key_Tab and
                self._completer.popup().isVisible()):
                    event.ignore()
                    return True
        return QtGui.QLineEdit.event(self, event)

    def do_completion(self):
        self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0,0))
        self._completer.complete()

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in self._keys_to_ignore:
                event.ignore()
                self._complete(self.last_word())
                return

        elif (event.key() == QtCore.Qt.Key_Down and
              self._completer.completionCount() > 0):
                event.accept()
                self.do_completion()
                return

        QtGui.QLineEdit.keyPressEvent(self, event)

        prefix = self.last_word()
        if prefix != unicode(self._completer.completionPrefix()):
            self._update_popup_items(prefix)
        if len(event.text()) > 0 and len(prefix) > 0:
            self._completer.complete()
        if len(prefix) == 0:
            self._completer.popup().hide()

    #: _drag: 0 - unclicked, 1 - clicked, 2 - dragged
    def mousePressEvent(self, event):
        self._drag = 1
        return QtGui.QLineEdit.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self._drag == 1:
            self._drag = 2
        return QtGui.QLineEdit.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self._drag != 2 and event.buttons() != QtCore.Qt.RightButton:
            self.do_completion()
        self._drag = 0
        return QtGui.QLineEdit.mouseReleaseEvent(self, event)

    def close_popup(self):
        self._completer.popup().close()

    def _update_popup_items(self, prefix):
        """
        Filters the completer's popup items to only show items
        with the given prefix.
        """
        self._completer.setCompletionPrefix(prefix)
        self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0,0))


class HighlightCompletionDelegate(QtGui.QStyledItemDelegate):
    """A delegate used for auto-completion to give formatted completion"""
    def __init__(self, parent=None): # model, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.highlight_text = ''
        self.case_sensitive = False

        self.doc = QtGui.QTextDocument()
        self.doc.setDocumentMargin(0)

    def set_highlight_text(self, text, case_sensitive):
        """Sets the text that will be made bold in the term name when displayed"""
        self.highlight_text = text
        self.case_sensitive = case_sensitive

    def paint(self, painter, option, index):
        """Overloaded Qt method for custom painting of a model index"""
        if not self.highlight_text:
            return QtGui.QStyledItemDelegate.paint(self, painter, option, index)

        text = unicode(index.data().toPyObject())
        if self.case_sensitive:
            html = text.replace(self.highlight_text,
                                '<strong>%s</strong>' % self.highlight_text)
        else:
            match = re.match('(.*)(' + self.highlight_text + ')(.*)',
                             text, re.IGNORECASE)
            if match:
                start = match.group(1) or ''
                middle = match.group(2) or ''
                end = match.group(3) or ''
                html = (start + ('<strong>%s</strong>' % middle) + end)
            else:
                html = text
        self.doc.setHtml(html)

        # Painting item without text, Text Document will paint the text
        optionV4 = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, index)
        optionV4.text = QtCore.QString()

        style = QtGui.QApplication.style()
        style.drawControl(QtGui.QStyle.CE_ItemViewItem, optionV4, painter)
        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected
        if (optionV4.state & QtGui.QStyle.State_Selected):
            ctx.palette.setColor(QtGui.QPalette.Text, optionV4.palette.color(QtGui.QPalette.Active, QtGui.QPalette.HighlightedText))
        # translate the painter to where the text is drawn
        textRect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, optionV4)
        painter.save()

        start = textRect.topLeft() + QtCore.QPoint(3, 0)
        painter.translate(start)
        painter.setClipRect(textRect.translated(-start))

        # tell the text document to draw the html for us
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()
def color(c, a=255):
    qc = QColor(c)
    qc.setAlpha(a)
    return qc

default_colors = {
    'color_add':            color(Qt.green, 128),
    'color_remove':         color(Qt.red,   128),
    'color_begin':          color(Qt.darkCyan),
    'color_header':         color(Qt.darkYellow),
    'color_stat_add':       color(QColor(32, 255, 32)),
    'color_stat_info':      color(QColor(32, 32, 255)),
    'color_stat_remove':    color(QColor(255, 32, 32)),
    'color_emphasis':       color(Qt.black),
    'color_info':           color(Qt.blue),
    'color_date':           color(Qt.darkCyan),
}
    dialog = SyntaxTestDialog(qtutils.active_window())