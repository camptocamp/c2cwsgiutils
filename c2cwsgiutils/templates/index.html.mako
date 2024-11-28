<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
    <link
      rel="icon"
      type="image/png"
      sizes="32x32"
      href="${request.static_url('c2cwsgiutils:static/favicon-32x32.png')}"
      referrerpolicy="no-referrer"
    />
    <link
      rel="icon"
      type="image/png"
      sizes="16x16"
      href="${request.static_url('c2cwsgiutils:static/favicon-16x16.png')}"
      referrerpolicy="no-referrer"
    />
    <link
        rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.3/css/bootstrap.min.css"
        integrity="sha512-jnSuA4Ss2PkkikSOLtYs8BlYIeeIK1h99ty4YfvRPAlzr377vr3CXDb7sb7eEEBYjDtcYj+AjBH3FLv5uSJuXg=="
        crossorigin="anonymous"
        referrerpolicy="no-referrer"
    />
    <title>C2C WSGI Utils tools</title>
    <style>
      body {
        margin-top: 0.5rem;
      }
      button, p  {
        margin-bottom: 0.5rem;
      }
      .row > h2 {
        margin-top: 1rem;
      }
    </style>
  </head>
  <body>
    <script>
      (() => {
        'use strict'
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
          document.documentElement.setAttribute('data-bs-theme', 'dark');
        }
      })()
    </script>
    <div class="container-fluid">
      ${ body | n }
    </div>
  </body>
</html>
