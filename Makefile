AGENTS_DIR := skills
DOCS_DIR := docs
EXTENDED_DIR := extended
DIR_TARGETS := .claude .cursor .windsurf .agent .gemini .agents

MD_SOURCE := AGENTS.md
MD_TARGETS := CLAUDE.md GEMINI.md

.PHONY: link link-dirs link-md link-extended unlink unlink-dirs unlink-md unlink-extended

link: link-dirs link-md link-extended

link-dirs:
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

link-md:
	@for target in $(MD_TARGETS); do \
		if [ -e "$$target" ] || [ -L "$$target" ]; then \
			echo "SKIP: $$target already exists"; \
		else \
			ln -s $(MD_SOURCE) $$target && echo "LINKED: $(MD_SOURCE) -> $$target"; \
		fi \
	done

link-extended:
	@if [ ! -d "$(EXTENDED_DIR)" ]; then \
		echo "SKIP: no $(EXTENDED_DIR)/ directory found"; \
		exit 0; \
	fi; \
	for skill_dir in $(EXTENDED_DIR)/*/; do \
		skill_name=$$(basename "$$skill_dir"); \
		target_dir="$$HOME/.claude/skills/$$skill_name"; \
		if [ ! -d "$$target_dir" ]; then \
			echo "SKIP: $$target_dir not found — install $$skill_name first"; \
			continue; \
		fi; \
		ext_skill="$$skill_dir/SKILL.md"; \
		if [ -f "$$ext_skill" ]; then \
			dest="$$target_dir/SKILL.extended.md"; \
			if [ -e "$$dest" ] || [ -L "$$dest" ]; then \
				echo "SKIP: $$dest already exists"; \
			else \
				ln -s "$$(pwd)/$$ext_skill" "$$dest" && echo "LINKED: $$ext_skill -> $$dest"; \
			fi; \
		fi; \
		ref_dir="$$skill_dir/reference"; \
		if [ -d "$$ref_dir" ]; then \
			dest="$$target_dir/reference"; \
			if [ -e "$$dest" ] || [ -L "$$dest" ]; then \
				echo "SKIP: $$dest already exists"; \
			else \
				ln -s "$$(pwd)/$$ref_dir" "$$dest" && echo "LINKED: $$ref_dir -> $$dest"; \
			fi; \
		fi; \
	done

unlink: unlink-dirs unlink-md unlink-extended

unlink-dirs:
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

unlink-md:
	@for target in $(MD_TARGETS); do \
		if [ -L "$$target" ]; then \
			rm $$target && echo "REMOVED: $$target"; \
		else \
			echo "SKIP: $$target is not a symlink"; \
		fi \
	done

unlink-extended:
	@if [ ! -d "$(EXTENDED_DIR)" ]; then \
		echo "SKIP: no $(EXTENDED_DIR)/ directory found"; \
		exit 0; \
	fi; \
	for skill_dir in $(EXTENDED_DIR)/*/; do \
		skill_name=$$(basename "$$skill_dir"); \
		target_dir="$$HOME/.claude/skills/$$skill_name"; \
		for item in SKILL.extended.md reference; do \
			dest="$$target_dir/$$item"; \
			if [ -L "$$dest" ]; then \
				rm "$$dest" && echo "REMOVED: $$dest"; \
			else \
				echo "SKIP: $$dest is not a symlink"; \
			fi; \
		done; \
	done
