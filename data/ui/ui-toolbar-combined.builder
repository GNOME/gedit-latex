<ui>
    <menubar name="MenuBar">
        <menu name="FileMenu" action="File">
            <placeholder name="FileOps_1">
                <menuitem action="LaTeXNewAction" />
            </placeholder>
        </menu>
        <placeholder name="ExtraMenu_1">
            <menu action="LaTeXMenuAction">
                <menuitem action="LaTeXChooseMasterAction" />
                <separator />
                <menuitem action="LaTeXGraphicsAction" />
                <menuitem action="LaTeXTableAction" />
                <menuitem action="LaTeXListingAction" />
                <menuitem action="LaTeXUseBibliographyAction" />
                <separator />
                <menuitem action="LaTeXCloseEnvironmentAction" />
                <separator />
                <menuitem action="LaTeXBuildImageAction" />
            </menu>
            <menu action="BibTeXMenuAction">
                <menuitem action="BibTeXNewEntryAction" />
            </menu>
        </placeholder>
    </menubar>
    <toolbar name="ToolBar">
        <separator />
        <toolitem action="LaTeXFontFamilyAction">
            <menu action="LaTeXFontFamilyMenuAction">
                <menuitem action="LaTeXBoldAction" />
                <menuitem action="LaTeXItalicAction" />
                <menuitem action="LaTeXEmphasizeAction" />
                <menuitem action="LaTeXUnderlineAction" />
                <menuitem action="LaTeXSmallCapitalsAction" />
                <menuitem action="LaTeXRomanAction" />
                <menuitem action="LaTeXSansSerifAction" />
                <menuitem action="LaTeXTypewriterAction" />
                <separator />
                <menuitem action="LaTeXBlackboardBoldAction" />
                <menuitem action="LaTeXCaligraphyAction" />
                <menuitem action="LaTeXFrakturAction" />
            </menu>
        </toolitem>
        <toolitem action="LaTeXJustifyActionDefault">
            <menu action="LaTeXJustifyMenuAction">
                <menuitem action="LaTeXJustifyLeftAction" />
                <menuitem action="LaTeXJustifyCenterAction" />
                <menuitem action="LaTeXJustifyRightAction" />
            </menu>
        </toolitem>
        <toolitem action="LaTeXListActionDefault">
            <menu action="LaTeXListMenuAction">
                <menuitem action="LaTeXItemizeAction" />
                <menuitem action="LaTeXEnumerateAction" />
                <menuitem action="LaTeXDescriptionAction" />
            </menu>
        </toolitem>
        <separator />
        <toolitem action="LaTeXStructureActionDefault">
            <menu action="LaTeXStructureMenuAction">
                <menuitem action="LaTeXPartAction" />
                <menuitem action="LaTeXChapterAction" />
                <separator />
                <menuitem action="LaTeXSectionAction" />
                <menuitem action="LaTeXSubsectionAction" />
                <menuitem action="LaTeXParagraphAction" />
                <menuitem action="LaTeXSubparagraphAction" />
            </menu>
        </toolitem>
        <separator />
        <toolitem action="LaTeXMathActionDefault">
            <menu action="LaTeXMathMenuAction">
                <menuitem action="LaTeXMathAction" />
                <menuitem action="LaTeXDisplayMathAction" />
                <menuitem action="LaTeXEquationAction" />
                <menuitem action="LaTeXUnEqnArrayAction" />
                <menuitem action="LaTeXEqnArrayAction" />
            </menu>
        </toolitem>
        <separator />
        <toolitem action="LaTeXGraphicsAction" />
        <toolitem action="LaTeXTableAction" />
        <toolitem action="LaTeXListingAction" />
        <toolitem action="LaTeXUseBibliographyAction" />
        <separator />
        <toolitem action="LaTeXBuildAction">
            <menu action="LaTeXBuildMenuAction">
                <menuitem action="LaTeXBuildImageAction" />
                <placeholder name="LaTeXBuildPlaceholder_1" />
            </menu>
        </toolitem>                
    </toolbar>
</ui>

