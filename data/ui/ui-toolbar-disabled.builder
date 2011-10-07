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
</ui>

