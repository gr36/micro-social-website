# micro social Website

This is the official website for micro social, a modern iOS client for Micro.blog. The website is built using Hugo, a fast and flexible static site generator.

## Prerequisites

- Hugo Extended v0.147.0 or later
- Node.js (for development tools if needed)

## Local Development

1. Clone this repository:
```bash
git clone https://github.com/yourusername/micro-social-website.git
cd micro-social-website
```

2. Start the Hugo development server:
```bash
hugo server -D
```

The site will be available at `http://localhost:1313/`

## Directory Structure

- `content/` - All content files (blog posts, etc.)
- `layouts/` - HTML templates
- `static/` - Static assets (images, CSS, JavaScript)
- `assets/` - Source files that require processing

## Creating New Content

To create a new blog post:

```bash
hugo new blog/my-new-post.md
```

## Building for Production

To build the site for production:

```bash
hugo --minify
```

The built site will be in the `public/` directory.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 