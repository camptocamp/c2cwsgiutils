DOT_FILES += $(shell find -name "*.dot" -print)
GEN_DOT_FILES +=  $(DOT_FILES:.dot=.png)

all: $(GEN_DOT_FILES) remark-latest.min.js

%.png: %.dot
	dot -Tpng $< > $@

remark-latest.min.js:
	curl https://remarkjs.com/downloads/remark-latest.min.js > $@

clean:
	rm -f $(GEN_DOT_FILES) remark-latest.min.js
