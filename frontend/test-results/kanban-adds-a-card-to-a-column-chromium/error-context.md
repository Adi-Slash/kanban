# Page snapshot

```yaml
- generic [ref=e1]:
  - main [ref=e2]:
    - generic [ref=e3]:
      - paragraph [ref=e4]: Project Management
      - heading "Sign in" [level=1] [ref=e5]
      - paragraph [ref=e6]: "Sign in to access your boards. Demo: user / password"
      - generic [ref=e7]:
        - generic [ref=e8]:
          - generic [ref=e9]: Username
          - textbox "Username" [ref=e10]: user
        - generic [ref=e11]:
          - generic [ref=e12]: Password
          - textbox "Password" [ref=e13]: password
        - alert [ref=e14]: Invalid credentials.
        - button "Sign in" [active] [ref=e15]
      - paragraph [ref=e16]:
        - text: New here?
        - button "Create an account" [ref=e17]
  - button "Open Next.js Dev Tools" [ref=e23] [cursor=pointer]:
    - img [ref=e24]
  - alert [ref=e27]
```