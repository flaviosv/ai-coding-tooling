AGENTS_DIR := skills
DOCS_DIR := docs
DIR_TARGETS := .claude .cursor .windsurf .agent .gemini .agents

MD_SOURCE := AGENTS.md
MD_TARGETS := CLAUDE.md GEMINI.md

.PHONY: link unlink

link:
	@for target in $(DIR_TARGETS); do \
		mkdir -p "$$target" && \
		if [ -e "$$target/skills" ] || [ -L "$$target/skills" ]; then \
			echo "SKIP: $$target/skills already exists"; \
		else \
			ln -s "../$(AGENTS_DIR)" "$$target/skills" && echo "LINKED: $(AGENTS_DIR) -> $$target/skills"; \
		fi; \
		if [ -e "$$target/docs" ] || [ -L "$$target/docs" ]; then \
			echo "SKIP: $$target/docs already exists"; \
		else \
			ln -s "../$(DOCS_DIR)" "$$target/docs" && echo "LINKED: $(DOCS_DIR) -> $$target/docs"; \
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
		if [ -L "$$target/skills" ]; then \
			rm "$$target/skills" && echo "REMOVED: $$target/skills"; \
		else \
			echo "SKIP: $$target/skills is not a symlink"; \
		fi; \
		if [ -L "$$target/docs" ]; then \
			rm "$$target/docs" && echo "REMOVED: $$target/docs"; \
		else \
			echo "SKIP: $$target/docs is not a symlink"; \
		fi \
	done
	@for target in $(MD_TARGETS); do \
		if [ -L "$$target" ]; then \
			rm $$target && echo "REMOVED: $$target"; \
		else \
			echo "SKIP: $$target is not a symlink"; \
		fi \
	done
