/**
 * XHS Content Extractor
 * 在浏览器端执行，提取小红书笔记内容
 */

(function() {
    'use strict';

    const XHSExtractor = {
        /**
         * 提取完整笔记信息
         */
        extract() {
            return {
                title: this.extractTitle(),
                author: this.extractAuthor(),
                content: this.extractContent(),
                tags: this.extractTags(),
                comments: this.extractComments(15),
                images: this.extractImages(),
                stats: this.extractStats()
            };
        },

        /**
         * 提取标题
         */
        extractTitle() {
            return document.title.replace(' - 小红书', '').trim();
        },

        /**
         * 提取作者
         */
        extractAuthor() {
            const selectors = [
                '.author-wrapper .name',
                '.author-info .nickname',
                '.user-info .name',
                '[class*="author"] [class*="name"]'
            ];
            
            for (const selector of selectors) {
                const el = document.querySelector(selector);
                if (el) {
                    return el.textContent.trim().replace(/\s+/g, ' ');
                }
            }
            
            return '未知作者';
        },

        /**
         * 提取正文内容
         */
        extractContent() {
            let bestContent = '';
            const divs = document.querySelectorAll('div');
            
            for (const div of divs) {
                const text = div.textContent.trim();
                // 筛选条件：长度合适、不是页脚内容
                if (text.length > bestContent.length && 
                    text.length < 3000 &&
                    !text.includes('ICP备') &&
                    !text.includes('营业执照') &&
                    !text.includes('去首页')) {
                    bestContent = text;
                }
            }
            
            return bestContent;
        },

        /**
         * 提取标签
         */
        extractTags() {
            const tagSet = new Set();
            const links = document.querySelectorAll('a');
            
            for (const link of links) {
                const text = link.textContent.trim();
                if (text.startsWith('#') && text.length > 2 && text.length < 30) {
                    tagSet.add(text.slice(1));
                }
            }
            
            return Array.from(tagSet).slice(0, 10);
        },

        /**
         * 提取评论
         */
        extractComments(limit = 15) {
            const comments = [];
            const items = document.querySelectorAll('.comment-item, .comment, [class*="comment"]');
            
            for (let i = 0; i < Math.min(items.length, limit); i++) {
                const item = items[i];
                const userEl = item.querySelector('.user-name, .nickname, [class*="user"]');
                const textEl = item.querySelector('.text, .content, [class*="text"]');
                
                if (userEl && textEl) {
                    const user = userEl.textContent.trim();
                    const text = textEl.textContent.trim();
                    if (user && text && text.length > 2) {
                        comments.push({ user, text });
                    }
                }
            }
            
            return comments;
        },

        /**
         * 提取图片URL
         */
        extractImages() {
            const images = [];
            const imgs = document.querySelectorAll('img');
            
            for (const img of imgs) {
                const src = img.src;
                if (src && 
                    src.includes('xiaohongshu') && 
                    !src.includes('avatar') &&
                    !src.includes('icon')) {
                    images.push(src);
                }
            }
            
            // 去重
            return [...new Set(images)];
        },

        /**
         * 提取互动数据
         */
        extractStats() {
            const text = document.body.textContent;
            const likeMatch = text.match(/(\d+)\s*赞/);
            const commentMatch = text.match(/共\s*(\d+)\s*条评论/);
            
            return {
                likes: likeMatch ? parseInt(likeMatch[1]) : 0,
                commentCount: commentMatch ? parseInt(commentMatch[1]) : 0
            };
        },

        /**
         * 滚动加载更多内容
         */
        async scrollToLoad() {
            for (let i = 0; i < 3; i++) {
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 1500));
            }
        }
    };

    // 如果是直接执行（通过 CDP evaluate）
    if (typeof window !== 'undefined') {
        return XHSExtractor.extract();
    }

    // 导出供其他模块使用
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = XHSExtractor;
    }
})();
