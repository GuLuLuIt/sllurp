from pathlib import Path

path = Path(__file__).with_name("_finish_runtime_todos.py")
text = path.read_text()
start = text.index("# Resume from PAUSED with no reader-side ROSpec")
end = text.index("replace_method(\n    \"sendMessage\"", start)
replacement = r"""# Resume safely when a paused ROSpec was removed/regenerated.
replace_method(
    "_resume_inventory",
    '''    def _resume_inventory(self, force_regen_rospec=False):
        logger.debugfast("resuming, force_regen_rospec=%s", force_regen_rospec)

        if self.state in (
            LLRPReaderState.STATE_CONNECTED,
            LLRPReaderState.STATE_DISCONNECTED,
        ):
            logger.debugfast("will startInventory()")
            self.startInventory(force_regen_rospec=force_regen_rospec)
            return

        if self.state != LLRPReaderState.STATE_PAUSED:
            logger.debugfast(
                "cannot resume() if not paused (state=%s); ignoring",
                LLRPReaderState.getStateName(self.state),
            )
            return None

        if self.rospec is None:
            self.setState(LLRPReaderState.STATE_CONNECTED)
            self.startInventory(force_regen_rospec=True)
            return

        if force_regen_rospec:
            def deleted(state, is_success, *args):
                if not is_success:
                    self.complain(None, "resume() could not replace paused ROSpec")
                    return
                self.setState(LLRPReaderState.STATE_CONNECTED)
                self.startInventory(force_regen_rospec=True)

            self.stopAllROSpecs(onCompletion=deleted)
            return

        logger.info("resuming")

        def enable_rospec_resume_cb(state, is_success, *args):
            if is_success:
                self.setState(LLRPReaderState.STATE_INVENTORYING)
            else:
                self.complain(None, "resume() failed")

        self.send_ENABLE_ROSPEC(None, self.rospec, onCompletion=enable_rospec_resume_cb)
''',
)

"""
text = text[:start] + replacement + text[end:]
path.write_text(text)
Path(__file__).unlink()
