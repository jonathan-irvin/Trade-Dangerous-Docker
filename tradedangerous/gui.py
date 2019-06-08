# --------------------------------------------------------------------
# Copyright (C) Oliver 'kfsone' Smith 2014 <oliver@kfs.org>:
# Copyright (C) Bernd 'Gazelle' Gollesch 2016, 2017
# Copyright (C) Jonathan 'eyeonus' Jones 2018, 2019
#
# You are free to use, redistribute, or even print and eat a copy of
# this software so long as you include this copyright notice.
# I guarantee there is at least one bug neither of us knew about.
# --------------------------------------------------------------------
# TradeDangerous :: Command Line App :: Main Module
#
# TradeDangerous is a powerful set of tools for traders in Frontier
# Development's game "Elite: Dangerous". It's main function is
# calculating the most profitable trades between either individual
# stations or working out "profit runs".
#
# I wrote TD because I realized that the best trade run - in terms
# of the "average profit per stop" was rarely as simple as going
# Chango -> Dahan -> Chango.
#
# E:D's economy is complex; sometimes you can make the most profit
# by trading one item A->B and flying a second item B->A.
# But more often you need to fly multiple stations, especially since
# as you are making money different trade options are coming into
# your affordable range.
#
# END USERS: If you are a user looking to find out how to use TD,
# please consult the file "README.md".
#
# DEVELOPERS: If you are a programmer who wants TD to do something
# cool, please see the TradeDB and TradeCalc modules. TD is designed
# to empower other programmers to do cool stuff.

from __future__ import absolute_import
from __future__ import with_statement
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
import os
import sys

from pathlib import Path
from appJar import gui
import appJar
from _ast import arg
from . import commands
from . import plugins
from .commands import exceptions
from .version import __version__

from . import tradedb

WIDGET_NAMES = appJar.appjar.WIDGET_NAMES

# Plugins available to the 'import' command are stored here.
# The list is populated by scanning the plugin folder directly,
# so it updates automagically at start as plugins are added or removed.
#
# Any other command with available plugins must have a similar list.
importPlugs = [ plug.name[0:plug.name.find('_plug.py')]
             for plug in os.scandir(sys.modules['tradedangerous.plugins'].__path__[0])
             if plug.name.endswith("_plug.py")
             ]

cwd = os.getcwd()
db = tradedb.TradeDB().dbFilename


# @Override
def _populateSpinBox(self, spin, vals, reverse = True):
    # make sure it's a list
    #  reverse it, so the spin box functions properly
    # if reverse:
    #    vals = list(vals)
    #    vals.reverse()
    vals = tuple(vals)
    spin.config(values = vals)


gui._populateSpinBox = _populateSpinBox


# @Override
def setSpinBoxPos(self, title, pos, callFunction = True):
    spin = self.widgetManager.get(WIDGET_NAMES.SpinBox, title)
    vals = spin.cget("values")  # .split()
    vals = self._getSpinBoxValsAsList(vals)
    pos = int(pos)
    if pos < 0 or pos >= len(vals):
        raise Exception("Invalid position: " + str(pos) + ". No position in SpinBox: " + 
                    title + "=" + str(vals))
    #    pos = len(vals) - 1 - pos
    val = vals[pos]
    self._setSpinBoxVal(spin, val, callFunction)


gui.setSpinBoxPos = setSpinBoxPos


def main(argv = None):
    sys.argv = ['trade']
    if not argv:
        argv = sys.argv
    if sys.hexversion < 0x03040200:
        raise SystemExit(
            "Sorry: TradeDangerous requires Python 3.4.2 or higher.\n"
            "For assistance, see:\n"
            "\tBug Tracker: https://github.com/eyeonus/Trade-Dangerous/issues\n"
            "\tDocumentation: https://github.com/eyeonus/Trade-Dangerous/wiki\n"
            "\tEDForum Thread: https://forums.frontier.co.uk/showthread.php/441509\n"
            )
    from . import tradeexcept
    
    # All available commands
    Commands = ['help'] + [ cmd for cmd, module in sorted(commands.commandIndex.items()) ]
    # Used to run TD cli commands.
    cmdIndex = commands.commandIndex
    cmdenv = commands.CommandIndex().parse
    # 'help' output, required & optional arguments, for each command
    cmdHelp, reqArg, optArg = dict(), dict(), dict()
    
    try:
        cmdenv(['help'])
    except exceptions.UsageError as e:
        cmdHelp['help'] = str(e)
    for cmd in Commands:
        # print(cmd)
        if cmd == 'help':
            continue
        try:
            cmdenv(['trade', cmd, '-h'])
        except exceptions.UsageError as e:
            cmdHelp[cmd] = str(e)
        index = cmdIndex[cmd]
        
        if index.arguments:
            reqArg[cmd] = {arg.args[0]: arg.kwargs for arg in index.arguments}
        else:
            reqArg[cmd] = dict()
        # print(reqArg[cmd])
        
        if index.switches:
            optArg[cmd] = dict()
            for arg in index.switches:
                try:
                    optArg[cmd][arg.args[0]] = {kwarg : arg.kwargs[kwarg] for kwarg in arg.kwargs}
                    if arg.args[0] == '--option':
                        # Currently only the 'import' cmd has the '--plug' option,
                        # but this could no longer be the case in future.
                        if cmd == 'import':
                            plugOptions = {
                                plug: plugins.load(cmdenv(['trade', cmd, '--plug', plug, '-O', 'help']).plug,
                                                    "ImportPlugin").pluginOptions for plug in importPlugs
                                }
                            optArg[cmd][arg.args[0]]['options'] = plugOptions
                        
                except AttributeError:
                    for argGrp in arg.arguments:
                        optArg[cmd][argGrp.args[0]] = {kwarg : argGrp.kwargs[kwarg] for kwarg in argGrp.kwargs}
                        
                        optArg[cmd][argGrp.args[0]]['excludes'] = [excl.args[0] for excl in arg.arguments 
                                                                   if excl.args[0] != argGrp.args[0]]
                        if argGrp.args[0] == '--plug':
                            # Currently only the 'import' cmd has the '--plug' option,
                            # but this could no longer be the case in future.
                            if cmd == 'import':
                                optArg[cmd][argGrp.args[0]]['plugins'] = importPlugs
        else:
            optArg[cmd] = dict()
        # print(optArg[cmd])
    
    def updCmd():
        cmd = win.combo("Command")
        print(cmd)
        
        win.message("helpText", cmdHelp[cmd])
        win.emptyScrollPane('reqArg')
        win.emptyScrollPane('optArg')
        if cmd == 'help':
            return
        if reqArg[cmd]:
            with win.scrollPane('reqArg', disabled = 'horizontal'):
                win.label('Required:', sticky = 'w')
                for key in reqArg[cmd]:
                    if '--c' in key:
                        win.entry(key, 0, tooltip = reqArg[cmd][key]['help'],
                                  label = True, sticky = 'ew')
                    else:
                        # All other required arguments are strings.
                        win.entry(key, label = True, sticky = 'ew', tooltip = reqArg[cmd][key]['help'])
        
        if optArg[cmd]:
            with win.scrollPane('optArg', disabled = 'horizontal'):
                win.label('Optional:', sticky = 'w')
                for key in optArg[cmd]:
                    arg = optArg[cmd][key]
                    if arg.get('excludes'):
                        print(key + " excludes: " + str(arg['excludes']))
                    # TODO: Populate pane with arguments.
                    # 'action':'store_true' -> check
                    # 'type':<class 'int'> -> spin(range(255 / 4095 ?))
                    # 'type':<class 'float'> -> entry(numeric)
                    # 'type':'type':'credits' -> entry
                    # if arg.get('choices') -> spin(['y','n','?'] / ['s','m','l','?'])
                    # 'type':'planetary' -> combo(ticks['y','n','?'])
                    # 'type':'padsize' -> combo(ticks['s','m','l','?'])
                    # 'action':'store_const' -> check
                    # '--option' -> custom handling
                    # 'type':<class 'str'> -> entry
                    # Everything else -> entry
                    # if arg.get('excludes') -> resetOther(arg['excludes'])
    
    def reset(name):
        if name == '--quiet' and int(win.spin('--quiet')) > 0:
            win.spin('--detail', 0)
        if name == '--detail' and int(win.spin('--detail')) > 0:
            win.spin('--quiet', 0)
            
    def changeCWD():
        """
        Opens a folder select dialog.
        """
        global cwd
        cwd = win.directoryBox("Select the top-level folder for TD to work in...", dirName = cwd) or cwd
        win.label('cwd', str(Path(cwd)))
        
    def changeDB():
        """
        Opens a file select dialog.
        """
        global db
        db = win.openBox("Select the TD database file to use...", dirName = str(Path(db).parent),
                          fileTypes = [('Data Base File', '*.db')]) or db
        win.label('db', str(Path(db)))
        
    def runTD():
        """
        Executes the TD command selected in the GUI.
        """
        # TODO: Implement running commands.
    
    with gui('Trade Dangerous GUI (Beta), TD v.%s' % (__version__,)) as win:
        win.combo('Command', Commands, change = updCmd, stretch = 'none', sticky = 'W',
                   width = 10, row = 0, column = 0, colspan = 5)
        with win.scrollPane('reqArg', disabled = 'horizontal', row = 1, column = 0, colspan = 25) as pane:
            pane.configure(width = 280, height = 100)
        
        with win.scrollPane('optArg', disabled = 'horizontal', row = 1, column = 25, colspan = 25) as pane:
            pane.configure(width = 280, height = 100)
        
        with win.scrollPane('helpPane', disabled = 'horizontal', colspan = 50) as pane:
            pane.configure(width = 560, height = 420)
            win.message("helpText", cmdHelp['help'])
        
        win.entry('--link-ly', 30.0, tooltip = 'Maximum lightyears between systems to be considered linked.',
                  label = True, kind = 'numeric', sticky = 'w', width = 4, row = 3, column = 2)
        win.spin('--quiet', [*range(4)], change = reset, tooltip = 'Reduce level of detail in output.',
                 label = True, selected = 0, sticky = 'e', width = 1, row = 3, column = 46)
        
        win.spin('--detail', [*range(4)], change = reset, tooltip = 'Increase level of detail in output.',
                 label = True, selected = 0, sticky = 'e', width = 1, row = 3, column = 47)
        
        win.spin('--debug', [*range(4)], tooltip = 'Enable/raise level of diagnostic output.',
                 label = True, selected = 0, sticky = 'e', width = 1, row = 3, column = 48)
        
        win.button('Run', runTD, tooltip = 'Execute the selected command.',
                   sticky = 'w', row = 3, column = 49)
        
        win.button('--cwd', changeCWD, tooltip = 'Change the working directory file accesses are made from.',
                   sticky = 'ew', width = 4, row = 4, column = 0)
        with win.scrollPane('CWD', disabled = 'vertical', row = 4, column = 1, colspan = 49) as pane:
            pane.configure(width = 500, height = 20)
            win.label('cwd', str(Path(cwd)), sticky = 'w')
        
        win.button('--db', changeDB, tooltip = 'Specify location of the SQLite database.',
                   sticky = 'ew', width = 4, row = 5, column = 0)
        with win.scrollPane('DB', disabled = 'vertical', row = 5, column = 1, colspan = 49) as pane:
            pane.configure(width = 500, height = 20)
            win.label('db', str(Path(db)), sticky = 'w')
        
    # End of window
    
#    try:
#        try:
#            if "CPROF" in os.environ:
#                import cProfile
#                cProfile.run("trade(argv)")
#            else:
#                trade(argv)
#        except PluginException as e:
#            print("PLUGIN ERROR: {}".format(e))
#            if 'EXCEPTIONS' in os.environ:
#                raise e
#            sys.exit(1)
#        except tradeexcept.TradeException as e:
#            print("%s: %s" % (argv[0], str(e)))
#            if 'EXCEPTIONS' in os.environ:
#                raise e
#            sys.exit(1)
#    except (UnicodeEncodeError, UnicodeDecodeError) as e:
#        print("-----------------------------------------------------------")
#        print("ERROR: Unexpected unicode error in the wild!")
#        print()
#        print(traceback.format_exc())
#        print(
#            "Please report this bug (http://kfs.org/td/issues). You may be "
#            "able to work around it by using the '-q' parameter. Windows "
#            "users may be able to use 'chcp.com 65001' to tell the console "
#            "you want to support UTF-8 characters."
#        )


def trade(argv):
    """
    This method represents the trade command.
    """
    cmdIndex = commands.CommandIndex()
    cmdenv = cmdIndex.parse(argv)
    
    tdb = tradedb.TradeDB(cmdenv, load = cmdenv.wantsTradeDB)
    if cmdenv.usesTradeData:
        tsc = tdb.tradingStationCount
        if tsc == 0:
            raise exceptions.NoDataError(
                "There is no trading data for ANY station in "
                "the local database. Please enter or import "
                "price data."
            )
        if tsc == 1:
            raise exceptions.NoDataError(
                "The local database only contains trading data "
                "for one station. Please enter or import data "
                "for additional stations."
            )
        if tsc < 8:
            cmdenv.NOTE(
                "The local database only contains trading data "
                "for {} stations. Please enter or import data "
                "for additional stations.".format(
                    tsc
                )
            )
    
    try:
        results = cmdenv.run(tdb)
    finally:
        # always close tdb
        tdb.close()
    
    if results:
        results.render()
