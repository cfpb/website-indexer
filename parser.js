import md5 from 'md5';
import cheerio from 'cheerio';
import { minify } from 'html-minifier-terser';

// Most of this parsing logic is copied from
// https://github.com/cfpb/cfgov-crawler-app/blob/master/src/models/page-model.js

class Parser {
  constructor (domBuffer) {
    this.html = domBuffer.toString();
    this.$ = cheerio.load(domBuffer);
  }

  getLinks () {
    const links = [];
    const $body = this.$('body');
    $body.find('.o-header').remove();
    $body.find('.o-footer').remove();
    $body.find('a').each((i, ele) => {
      const href = this.$(ele).attr('href');
      if (typeof (href) !== 'undefined') {
        links.push(href);
      }
    });

    return links;
  }

  getHash () {
    return md5(this.html);
  }

  async getHtml () {
    let html = this.html;
    try {
      return await minify(this.html, { collapseWhitespace: true });
    } catch (error) {
      return html;
    }
  }

  getTitle () {
    return this.$('title').text();
  }

  getComponents () {
    const SEARCH = /(?:(?:class=")|\s)((?:o|m|a)-[^_"__\s]*)/g;
    const pageHMTL = this.html.toString();
    const prefixLookup = [
      'a-',
      'm-',
      'o-'
    ];
    let matchType;
    const components = [];
    let match;
    while ((match = SEARCH.exec(pageHMTL)) !== null) {
      match.forEach(function (match, groupIndex) {
        matchType = match.substr(0, 2);
        if ((prefixLookup.indexOf(matchType) > -1) &&
            (components.indexOf(match) === -1)) {
          components.push(match);
        }
      });
    }

    return components;
  }
}

export default Parser;
