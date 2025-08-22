import { test, expect } from "@playwright/test";

test.describe("Messages", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to messages page
    await page.goto("/messages");
  });

  test("should display empty state when no threads exist", async ({ page }) => {
    // Should show empty state
    await expect(page.getByText("No conversations yet")).toBeVisible();
    await expect(page.getByText("Start your first conversation")).toBeVisible();
  });

  test("should create a new thread", async ({ page }) => {
    // Click new thread button
    await page.getByRole("button", { name: "New Conversation" }).click();

    // Fill in thread details
    await page
      .getByPlaceholder("Enter a title for this conversation")
      .fill("Test Conversation");
    await page
      .getByPlaceholder("Start the conversation...")
      .fill("Hello, this is a test message");

    // Submit
    await page.getByRole("button", { name: "Create" }).click();

    // Should navigate to the new thread and show the message
    await expect(page.getByText("Test Conversation")).toBeVisible();
    await expect(page.getByText("Hello, this is a test message")).toBeVisible();
  });

  test("should send a message in a thread", async ({ page }) => {
    // Mock API responses
    await page.route("**/api/chat/threads", async (route) => {
      await route.fulfill({
        json: [
          {
            id: "test-thread-1",
            title: "Test Thread",
            created_at: new Date().toISOString(),
            lastMessage: {
              id: "msg-1",
              content: "Previous message",
              type: "user",
              created_at: new Date().toISOString(),
            },
          },
        ],
      });
    });

    await page.route("**/api/chat/threads/test-thread-1", async (route) => {
      await route.fulfill({
        json: {
          id: "test-thread-1",
          title: "Test Thread",
          created_at: new Date().toISOString(),
        },
      });
    });

    await page.route(
      "**/api/chat/threads/test-thread-1/messages",
      async (route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            json: [
              {
                id: "msg-1",
                content: "Previous message",
                type: "user",
                created_at: new Date().toISOString(),
              },
            ],
          });
        } else if (route.request().method() === "POST") {
          const body = await route.request().postDataJSON();
          await route.fulfill({
            json: {
              id: "msg-2",
              content: body.content,
              type: body.type,
              created_at: new Date().toISOString(),
            },
          });
        }
      },
    );

    await page.reload();

    // Select the thread
    await page.getByText("Test Thread").click();

    // Type and send a message
    const composer = page.getByPlaceholder("Type your message...");
    await composer.fill("This is a test message");
    await page.getByRole("button", { name: "Send message" }).click();

    // Should show the message
    await expect(page.getByText("This is a test message")).toBeVisible();
  });

  test("should attach message to IEP evidence", async ({ page }) => {
    // Mock API responses including consent check
    await page.route("**/api/chat/consent/iep-attachment", async (route) => {
      await route.fulfill({ json: { hasConsent: true } });
    });

    await page.route("**/api/chat/threads", async (route) => {
      await route.fulfill({
        json: [
          {
            id: "test-thread-1",
            title: "Test Thread",
            created_at: new Date().toISOString(),
            lastMessage: {
              id: "msg-1",
              content: "AI response message",
              type: "assistant",
              created_at: new Date().toISOString(),
            },
          },
        ],
      });
    });

    await page.route("**/api/chat/threads/test-thread-1", async (route) => {
      await route.fulfill({
        json: {
          id: "test-thread-1",
          title: "Test Thread",
          created_at: new Date().toISOString(),
        },
      });
    });

    await page.route(
      "**/api/chat/threads/test-thread-1/messages",
      async (route) => {
        await route.fulfill({
          json: [
            {
              id: "ai-msg-1",
              content: "This is an AI response with valuable insights",
              type: "assistant",
              created_at: new Date().toISOString(),
            },
          ],
        });
      },
    );

    await page.route(
      "**/api/chat/messages/ai-msg-1/iep-attachment",
      async (route) => {
        await route.fulfill({ json: { success: true } });
      },
    );

    await page.reload();

    // Select the thread
    await page.getByText("Test Thread").click();

    // Click attach to IEP button on AI message
    await page.getByText("Attach to IEP Evidence").click();

    // Fill in IEP attachment form
    await page.getByRole("combobox").selectOption("observation");
    await page
      .getByPlaceholder("Brief description of this evidence")
      .fill("AI insight on student behavior");
    await page
      .getByPlaceholder("Add context or observations")
      .fill("Generated during chat session");

    // Submit attachment
    await page.getByRole("button", { name: "Attach to IEP" }).click();

    // Modal should close
    await expect(page.getByText("Attach to IEP Evidence")).not.toBeVisible();
  });

  test("should show consent required dialog when no consent", async ({
    page,
  }) => {
    // Mock API responses with no consent
    await page.route("**/api/chat/consent/iep-attachment", async (route) => {
      await route.fulfill({ json: { hasConsent: false } });
    });

    await page.route("**/api/chat/threads", async (route) => {
      await route.fulfill({
        json: [
          {
            id: "test-thread-1",
            title: "Test Thread",
            created_at: new Date().toISOString(),
            lastMessage: {
              id: "msg-1",
              content: "AI response message",
              type: "assistant",
              created_at: new Date().toISOString(),
            },
          },
        ],
      });
    });

    await page.route("**/api/chat/threads/test-thread-1", async (route) => {
      await route.fulfill({
        json: {
          id: "test-thread-1",
          title: "Test Thread",
          created_at: new Date().toISOString(),
        },
      });
    });

    await page.route(
      "**/api/chat/threads/test-thread-1/messages",
      async (route) => {
        await route.fulfill({
          json: [
            {
              id: "ai-msg-1",
              content: "This is an AI response with valuable insights",
              type: "assistant",
              created_at: new Date().toISOString(),
            },
          ],
        });
      },
    );

    await page.reload();

    // Select the thread
    await page.getByText("Test Thread").click();

    // Click attach to IEP button
    await page.getByText("Attach to IEP Evidence").click();

    // Should show consent required dialog
    await expect(page.getByText("Consent Required")).toBeVisible();
    await expect(
      page.getByText("consent for chat data sharing must be enabled"),
    ).toBeVisible();
  });

  test("should delete a thread", async ({ page }) => {
    // Mock API responses
    await page.route("**/api/chat/threads", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          json: [
            {
              id: "test-thread-1",
              title: "Test Thread to Delete",
              created_at: new Date().toISOString(),
              lastMessage: {
                id: "msg-1",
                content: "Test message",
                type: "user",
                created_at: new Date().toISOString(),
              },
            },
          ],
        });
      }
    });

    await page.route("**/api/chat/threads/test-thread-1", async (route) => {
      if (route.request().method() === "DELETE") {
        await route.fulfill({ json: { success: true } });
      }
    });

    await page.reload();

    // Hover over thread to show delete button
    await page.getByText("Test Thread to Delete").hover();

    // Click delete button
    await page.getByTitle("Delete").click();

    // Confirm deletion
    await page.getByRole("button", { name: "Delete" }).click();

    // Thread should be removed (back to empty state)
    await expect(page.getByText("Test Thread to Delete")).not.toBeVisible();
  });

  test("should work responsively on mobile", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Mock API response with threads
    await page.route("**/api/chat/threads", async (route) => {
      await route.fulfill({
        json: [
          {
            id: "test-thread-1",
            title: "Mobile Test Thread",
            created_at: new Date().toISOString(),
            lastMessage: {
              id: "msg-1",
              content: "Mobile message",
              type: "user",
              created_at: new Date().toISOString(),
            },
          },
        ],
      });
    });

    await page.route("**/api/chat/threads/test-thread-1", async (route) => {
      await route.fulfill({
        json: {
          id: "test-thread-1",
          title: "Mobile Test Thread",
          created_at: new Date().toISOString(),
        },
      });
    });

    await page.route(
      "**/api/chat/threads/test-thread-1/messages",
      async (route) => {
        await route.fulfill({
          json: [
            {
              id: "msg-1",
              content: "Mobile message",
              type: "user",
              created_at: new Date().toISOString(),
            },
          ],
        });
      },
    );

    await page.reload();

    // On mobile, should show thread list initially
    await expect(page.getByText("Mobile Test Thread")).toBeVisible();

    // Select thread - should hide thread list and show conversation
    await page.getByText("Mobile Test Thread").click();
    await expect(page.getByText("Mobile message")).toBeVisible();

    // Back button should be visible and work
    await page.getByTitle("Back").click();
    await expect(page.getByText("Mobile Test Thread")).toBeVisible();
  });

  test("should handle AI response streaming", async ({ page }) => {
    // Mock streaming response
    await page.route("**/api/inference/generate-stream", async (route) => {
      const response = new Response(
        'data: {"delta": {"content": "Hello "}}\n\ndata: {"delta": {"content": "there!"}}\n\ndata: [DONE]\n\n',
        {
          headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
          },
        },
      );
      await route.fulfill({ response });
    });

    await page.route("**/api/chat/threads", async (route) => {
      await route.fulfill({
        json: [
          {
            id: "test-thread-1",
            title: "Streaming Test",
            created_at: new Date().toISOString(),
            lastMessage: null,
          },
        ],
      });
    });

    await page.route("**/api/chat/threads/test-thread-1", async (route) => {
      await route.fulfill({
        json: {
          id: "test-thread-1",
          title: "Streaming Test",
          created_at: new Date().toISOString(),
        },
      });
    });

    await page.route(
      "**/api/chat/threads/test-thread-1/messages",
      async (route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({ json: [] });
        } else {
          const body = await route.request().postDataJSON();
          await route.fulfill({
            json: {
              id: "msg-user",
              content: body.content,
              type: body.type,
              created_at: new Date().toISOString(),
            },
          });
        }
      },
    );

    await page.reload();

    // Select thread and send message with AI enabled
    await page.getByText("Streaming Test").click();
    await page.getByPlaceholder("Type your message...").fill("Hello AI");
    await page.getByRole("button", { name: "Send message" }).click();

    // Should show AI typing indicator
    await expect(page.getByText("AI is typing...")).toBeVisible();
  });
});
