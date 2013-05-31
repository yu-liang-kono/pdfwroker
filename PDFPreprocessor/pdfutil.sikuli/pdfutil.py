# -*- coding: utf-8 -*-
from sikuli import *

# standard library imports
from fnmatch import fnmatch
import os
import os.path
import re
import shutil
import subprocess
import time
import uuid

# third party related imports

# local library imports
import savefiledlg
reload(savefiledlg)

# Control the time taken for mouse movement to a target location.
DEFAULT_MOUSE_DELAY = Settings.MoveMouseDelay
Settings.MoveMouseDelay = 0.1


ACROBAT_STATUS_BAR = "1369733764191.png"


class PDFUtilError(Exception): pass


class ActionWizard(object):
    """
    ActionWizard takes charge of executing a predefined Adobe Acrobat
    action.

    """
    
    CONVERT_SRGB = 'srgb'
    CONVERT_VTI = 'vti'
    ACTION_MENU_PATTERN = {
        CONVERT_SRGB: "1369734036721.png",
        CONVERT_VTI: "1369736894650.png",
    }
    ACTION_DONE_PATTERN = {
        CONVERT_SRGB: "1369735513576.png",
        CONVERT_VTI: "1369737125198.png",
    }
    
    def __init__(self, action):
        """Constructor. Must be a valid action name."""
        
        self.action_menu = self.ACTION_MENU_PATTERN[action]
        self.action_done_dlg = self.ACTION_DONE_PATTERN[action]

    def do_action(self, abs_output_dir, timeout=60):

        self._hover_action_wizard_menu()
        click(self.action_menu)
        savefiledlg.wait_dlg_popup(timeout)
        savefiledlg.find_target_dir(abs_output_dir)
        click(savefiledlg.SAVE_BUTTON)
        wait("1369889558051.png")
        click("1369889574993.png")
        
    def _hover_action_wizard_menu(self):
        
        _move_mouse_top()
        click(Pattern("1369733764191.png").targetOffset(80,0))
        hover("1369889288003.png")

        
def _create_desktop_tempdir_and_save():

    left_side_bar_header = find("1369734265216.png")
    
    try:
        desktop_label = left_side_bar_header.below().find("1369735187214.png")     
    except FindFailed:
        desktop_label = left_side_bar_header.below().find("1369734314261.png")
    finally:
        click(desktop_label)
           
    # create a temporary directory
    tempdir = uuid.uuid1().hex
    click("1369723600085.png")
    click(Pattern("1369723639913.png").targetOffset(0,27))
    type('a', KeyModifier.CMD)
    paste(tempdir)
    click("1369724048617.png")
    click("1369724174496.png")

    return tempdir


def _get_highlight_text():
    """Given the texts are highlighted, copy to clipboard and return."""

    type('a', KeyModifier.CMD)
    type('c', KeyModifier.CMD)

    cwd = os.path.dirname(getBundlePath())
    script_path = os.path.join(cwd, 'clipboard.scpt')
    
    try:
        p = subprocess.Popen(["osascript", script_path],
                             stdout=subprocess.PIPE)
    except OSError, e:
        print unicode(e)
        return None

    out, err = p.communicate()
    
    return out


def _move_mouse_top():
    """Move mouse to the top status bar."""

    loc = Env.getMouseLocation()
    loc.setLocation(loc.getX(), 0)
    mouseMove(loc)
    
    
def get_num_pages(abs_filename):
    """Get the number of pages in a pdf."""

    try:
        p = subprocess.Popen(
                ('pdftk', abs_filename, 'dump_data', 'output'),
                stdout=subprocess.PIPE
            )
    except OSError, e:
        print unicode(e)
        return 0

    out, err = p.communicate()
    for line in out.split('\n'):
        if 'NumberOfPages' in line:
            m = re.search(r'\d+', line)
            return int(line[m.start():m.end()])

    return 0


def open_pdf(abs_filename, timeout=10):
    """Open a pdf file by Adobe Acrobat X Pro application and wait until done."""

    try:
        p = subprocess.Popen(
                ('open', '-a', 'Adobe Acrobat Pro', abs_filename),
                stdout=subprocess.PIPE
            )
        wait("1369712063644.png", timeout)
    except OSError, e:
        print unicode(e)
        raise PDFUtilError('Error: open -a "Adobe Acrobat Pro" %s' % abs_filename) 
    except FindFailed, e:
        print unicode(e)
        raise PDFUtilError('Error: open %s timeout' % abs_filename)


def close_pdfs():
    """Close all opened pdf."""

    app = App('Adobe Acrobat Pro')
    while app.window():
        type('w', KeyModifier.CMD)
        wait(1)
        

    app.close()

    
def split(abs_filename, abs_output_dir):
    """Split the specified pdf into multiple pdf per page."""

    TIMEOUT = 5
    
    open_pdf(abs_filename)

    # jump to the end of pages
    click("1369712063644.png")
    
    # start extract pages  
    click("1369711747763.png")
    extract_dlg = wait("1369797890666.png", TIMEOUT)
    click(extract_dlg.getTarget().offset(28, -18))
    num_pages = int(_get_highlight_text()) 
    type('1')
    click(extract_dlg.getTarget().offset(-7, 29))
    click("1369723377211.png")

    # save to a directory in desktop directory
    savefiledlg.wait_dlg_popup(TIMEOUT)
    savefiledlg.find_target_dir(abs_output_dir)
    click(savefiledlg.SELECT_BUTTON)

    # wait until all pdf are dumped
    basename = os.path.basename(abs_filename)
    base, ext = os.path.splitext(basename)
    last_page_pdf = os.path.join(abs_output_dir,
                                 '%s %s.pdf' % (base, num_pages))
    while not os.path.exists(last_page_pdf):
        wait(5)

    # rename all dumped pdf
    for file in os.listdir(abs_output_dir):
        if fnmatch(file, '*.pdf'):
            base, ext = os.path.splitext(file)
            page = int(base.split(' ')[-1])
            shutil.move(os.path.join(abs_output_dir, file),
                        os.path.join(abs_output_dir, '%04d.pdf' % page))
            
    close_pdfs()
    
    return num_pages


def convert_srgb(abs_src, abs_output_dir):
    """Convert CMYK color space to sRGB color space."""
        
    open_pdf(abs_src)

    action = ActionWizard(ActionWizard.CONVERT_SRGB)
    action.do_action(abs_output_dir)

    close_pdfs()
    

def _move_tempdir_content_and_destroy(tempdir, abs_output_dir):

    tempdir = os.path.expanduser(os.path.join('~', 'Desktop', tempdir))
    for file in os.listdir(tempdir):
        if fnmatch(file, '*.pdf') or fnmatch(file, '*.tiff'):
            shutil.move(os.path.join(tempdir, file),
                        os.path.join(abs_output_dir, file))
            
    shutil.rmtree(tempdir)

    
def convert_vti(abs_src, abs_output_dir):
    """Split vector object, text object, image object into separate layers."""

    open_pdf(abs_src)

    action = ActionWizard(ActionWizard.CONVERT_VTI)
    action.do_action(abs_output_dir)
    
    close_pdfs()


def convert_tiff(abs_src, abs_output_dir):
    """Save pdf background as tiff."""

    open_pdf(abs_src)

    try:
        layer_btn = find("1369968652342.png")
        click(layer_btn)
    except FindFailed, e:
        print unicode(e)
        raise PDFUtilError('cannot find out layer button in left column.')

    try:
        text_layer_label = layer_btn.nearby(300).find("1369968826594.png")
        click(text_layer_label.getTarget().offset(-25, 0))
    except FindFailed, e:
        print unicode(e)
        print 'Maybe this page does not have text layer.'
        raise PDFUtilError('cannot find out text layer label in left column')

    # move mouse to the top
    _move_mouse_top()
    acrobat_pattern = find(ACROBAT_STATUS_BAR)
    view_pattern = acrobat_pattern.nearby(200).find("1369971004152.png")
    click(view_pattern)
    tool_pattern = view_pattern.nearby(150).find("1369804301256.png")
    hover(tool_pattern)
    protection_pattern = tool_pattern.nearby(150).find("1369804425199.png")
    click(protection_pattern)

    # remove hidden information
    target_action = wait("1369804512050.png", 5)
    click(target_action)
    complete_pattern = wait("1369804581481.png", 60)
    wait(1) # wait for all checkboxes appear

    # first uncheck all checkboxes
    map(lambda x: click(x), complete_pattern.below().findAll("1369808493670.png"))
           
    # check what we want
    try:
        hidden_text_label = complete_pattern.below().find("1369804767828.png")
        click(hidden_text_label.getTarget().offset(-30, 0))

        hidden_layer_label = hidden_text_label.nearby(150).find("1369804828198.png")
        click(hidden_layer_label.getTarget().offset(-30, 0))

        remove_btn = complete_pattern.below(150).find("1369804889386.png")
        click(remove_btn)
    except FindFailed, e:
        print unicode(e)
        raise PDFUtilError('cannot find out hidden text label')
    
    wait("1369804930217.png", 60)
    wait(1)

    # save as tiff
    _move_mouse_top()
    file_pattern = acrobat_pattern.nearby(150).find("1369971661059.png")
    click(file_pattern)
    save_as_pattern = file_pattern.nearby(150).find("1369971712516.png")
    hover(save_as_pattern)
    image_pattern = save_as_pattern.nearby(400).find("1369971777792.png")
    hover(image_pattern)
    tiff_pattern = image_pattern.nearby(100).find("1369971820441.png")
    click(tiff_pattern)

    # deal with save file dialog
    savefiledlg.wait_dlg_popup(5)
    tiff_config_region = find("1369805219651.png")
    click(tiff_config_region.getTarget().offset(130, 0))
    _configure_tiff_setting()
    savefiledlg.find_target_dir(abs_output_dir)
    click(tiff_config_region.nearby(125).find(savefiledlg.SAVE_BUTTON))

    # wait until tiff saved
    basename = os.path.basename(abs_src)
    base, ext = os.path.splitext(basename)
    output_tiff = os.path.join(abs_output_dir, '%s.tiff' % base)
    while not os.path.exists(output_tiff):
        wait(1)

    # quit
    type('w', KeyModifier.CMD)
    wait(0.25)
    try:
        quit_dlg = find(Pattern("1369815983577.png").targetOffset(-110,25))
        click(quit_dlg)
    except FindFailed:
        raise PDFUtilExit('cannot find confirm dialog')
        
    close_pdfs()


def _configure_tiff_setting():

    default_similarity = Settings.MinSimilarity
    Settings.MinSimilarity = 0.8
    tiff_config_dlg = wait("1369975556696.png", 5)
    tiff_config_region = tiff_config_dlg.below(400)
    
    f = capture(tiff_config_region.getX(), tiff_config_region.getY(),
                tiff_config_region.getW(), tiff_config_region.getH())
    shutil.move(f, '/Users/yuliang/Desktop/tiff.png')

    try:
        tiff_config_region.find("1369805438935.png")
        tiff_config_region.find("1369805554434.png")
        tiff_config_region.find("1369805636396.png")
        tiff_config_region.find("1369805847221.png")
        tiff_config_region.find("1369806047586.png")
        tiff_config_region.find("1369807167193.png")
    except FindFailed, e:
        print unicode(e)
        
        default_btn = tiff_config_region.find("1369807204426.png")
        click(default_btn)
        monochrome_opt = tiff_config_region.find("1369814699054.png")
        click(monochrome_opt.getTarget().offset(40, 0))
        click(monochrome_opt.nearby(100).find("1369807298142.png"))
        wait(0.25)

        grayscale_opt = monochrome_opt.nearby(150).find("1369814255357.png")
        click(grayscale_opt.getTarget().offset(40, 0))
        click(grayscale_opt.nearby(150).find("1369807366371.png"))
        wait(0.25)

        color_opt = grayscale_opt.nearby(150).find("1369814646106.png")
        click(color_opt.getTarget().offset(40, 0))
        click(color_opt.nearby(150).find("1369807366371.png"))
    finally:
        if 'default_btn' not in locals():
            default_btn = tiff_config_region.find("1369807204426.png")
        
    bottom_region = default_btn.nearby(100)
    f = capture(bottom_region.getX(), bottom_region.getY(),
                bottom_region.getW(), bottom_region.getH())
    shutil.copy(f, '/Users/yuliang/Desktop/bottom.png')
    
    if not bottom_region.exists("1369807501996.png"):
        color_space_opt = bottom_region.find("1369807517929.png")
        click(color_space_opt.getTarget().offset(40, 0))
        click(color_space_opt.nearby(150).find("1369807541423.png"))

    if not bottom_region.exists("1369807568436.png"):
        click(bottom_region.find(Pattern("1369807588124.png").targetOffset(40,0)))
        type('a', KeyModifier.CMD)
        paste(u' 600 像素 / 英吋')

    click(default_btn.right(200).find("1369807652267.png"))

    Settings.MinSimilarity = default_similarity
    

def merge_tiff_by_imagemagick(abs_src_dir, num_pages, abs_output_dir):
    """Merge all tiff files to a pdf."""

    cmd = ['convert']
    for i in xrange(1, num_pages + 1):
        cmd.append(os.path.join(abs_src_dir, '%s.tiff' % i))
    cmd.append(os.path.join(abs_output_dir, 'back.pdf'))
    print cmd
    
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError, e:
        print unicode(e)
        raise PDFUtilError('Error: merge tiff to back.pdf')

    out, err = p.communicate()


def merge_tiff(abs_src_dir, abs_output_dir):
    """Merge all tiff files to a pdf."""
    
    try:
        subprocess.Popen(['open', '-a', 'Adobe Acrobat Pro'])
        wait(1)
    except OSError, e:
        print unicode(e)
        raise PDFUtilError('Error: open Adobe Acrobat Pro')

    # move mouse to the top
    loc = Env.getMouseLocation()
    loc.setLocation(loc.getX(), 0)
    mouseMove(loc)
    click(Pattern("1369805010440.png").targetOffset(55,0))
    hover("1369824102358.png")
    click("1369824125882.png")
    wait("1369824157955.png", 5)
    click("1369824184003.png")
    click("1369824203704.png")
    search_box = wait("1369824244188.png", 5)
    click(search_box)
    paste(os.path.basename(abs_src_dir))

    click(Pattern("1369826469948.png").targetOffset(46,13))
    click("1369826526713.png")
    click("1369826623378.png")
    click("1369827319476.png")
    wait(1)
    waitVanish("1369828292764.png", FOREVER)
    wait(1)
    type('s', KeyModifier.CMD)

    tempdir = uuid.uuid1().hex
    os.mkdir(tempdir)
    search_box = wait("1369824244188.png", 5)
    click(search_box)
    paste(tempdir)
    click(Pattern("1369826469948.png").targetOffset(46,13))
    doubleClick("1369826526713.png")
    click("1369828946228.png")

    while True:
        files = filter(lambda f: fnmatch(f, '*.pdf'), os.listdir(tempdir))
        if len(files) == 0:
            wait(1)
            continue

        shutil.move(os.path.join(tempdir, files[0]),
                    os.path.join(abs_output_dir, 'back.pdf'))
        break
       
    shutil.rmtree(tempdir)


def convert_text(abs_src, abs_output_dir):
    """Merge to a pdf only containing texts."""

    