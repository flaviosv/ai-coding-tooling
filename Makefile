AGENTS_DIR := .agents
DIR_TARGETS := .claude .cursor .windsurf .agent .gemini

MD_SOURCE := AGENTS.md
MD_TARGETS := CLAUDE.md GEMINI.md

.PHONY: link unlink

link:
	@for target in $(DIR_TARGETS); do \
		if [ -e "$$target" ] || [ -L "$$target" ]; then \
			echo "SKIP: $$target already exists"; \
		else \
			ln -s $(AGENTS_DIR) $$target && echo "LINKED: $(AGENTS_DIR) -> $$target"; \
		fi \
	done
	@for target in $(MD_TARGETS); do \
		if [ -e "$$target" ] || [ -L "$$target" ]; then \
			echo "SKIP: $$target already exists"; \
		else \
			ln -s $(MD_SOURCE) $$target && echo "LINKED: $(MD_SOURCE) -> $$target"; \
		fi \
	done

unlink:
	@for target in $(DIR_TARGETS); do \
		if [ -L "$$target" ]; then \
			rm $$target && echo "REMOVED: $$target"; \
		else \
			echo "SKIP: $$target is not a symlink"; \
		fi \
	done
	@for target in $(MD_TARGETS); do \
		if [ -L "$$target" ]; then \
			rm $$target && echo "REMOVED: $$target"; \
		else \
			echo "SKIP: $$target is not a symlink"; \
		fi \
	done
