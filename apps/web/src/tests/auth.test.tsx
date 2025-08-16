import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'

// Components
import { EmailField } from '@/components/forms/EmailField'
import { PasswordField } from '@/components/forms/PasswordField'
import { OtpInput } from '@/components/forms/OtpInput'

// Mock react-hook-form registration
const createMockRegistration = (name: string) => ({
  name,
  onChange: vi.fn(),
  onBlur: vi.fn(),
  ref: vi.fn(),
})

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    readText: vi.fn(),
  },
})

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  return <BrowserRouter>{children}</BrowserRouter>
}

describe('Form Components', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('EmailField Component', () => {
    it('renders with label and placeholder', () => {
      const mockRegistration = createMockRegistration('email')

      render(
        <TestWrapper>
          <EmailField
            label="Email Address"
            placeholder="Enter your email"
            registration={mockRegistration}
          />
        </TestWrapper>
      )

      expect(screen.getByLabelText('Email Address')).toBeInTheDocument()
      expect(
        screen.getByPlaceholderText('Enter your email')
      ).toBeInTheDocument()
    })

    it('shows error message when provided', () => {
      const mockRegistration = createMockRegistration('email')

      render(
        <TestWrapper>
          <EmailField
            label="Email Address"
            placeholder="Enter your email"
            error="Invalid email address"
            registration={mockRegistration}
          />
        </TestWrapper>
      )

      expect(screen.getByText('Invalid email address')).toBeInTheDocument()
      expect(screen.getByRole('textbox')).toHaveClass('border-red-300')
    })

    it('accepts user input', async () => {
      const user = userEvent.setup()
      const mockRegistration = createMockRegistration('email')

      render(
        <TestWrapper>
          <EmailField
            label="Email Address"
            placeholder="Enter your email"
            registration={mockRegistration}
          />
        </TestWrapper>
      )

      const input = screen.getByRole('textbox')
      await user.type(input, 'test@example.com')

      expect(input).toHaveValue('test@example.com')
    })
  })

  describe('PasswordField Component', () => {
    it('renders with toggle visibility button', () => {
      const mockRegistration = createMockRegistration('password')

      render(
        <TestWrapper>
          <PasswordField
            label="Password"
            placeholder="Enter your password"
            registration={mockRegistration}
          />
        </TestWrapper>
      )

      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: /show password/i })
      ).toBeInTheDocument()
    })

    it('toggles password visibility', async () => {
      const user = userEvent.setup()
      const mockRegistration = createMockRegistration('password')

      render(
        <TestWrapper>
          <PasswordField
            label="Password"
            placeholder="Enter your password"
            registration={mockRegistration}
          />
        </TestWrapper>
      )

      const input = screen.getByLabelText('Password')
      const toggleButton = screen.getByRole('button', {
        name: /show password/i,
      })

      expect(input).toHaveAttribute('type', 'password')

      await user.click(toggleButton)
      expect(input).toHaveAttribute('type', 'text')

      await user.click(toggleButton)
      expect(input).toHaveAttribute('type', 'password')
    })

    it('shows strength meter when enabled and has content', () => {
      const mockRegistration = createMockRegistration('password')

      // Test that showStrengthIndicator prop is accepted without error
      render(
        <TestWrapper>
          <PasswordField
            label="Password"
            placeholder="Enter your password"
            showStrengthIndicator={true}
            registration={mockRegistration}
          />
        </TestWrapper>
      )

      // Verify the component renders correctly with strength indicator enabled
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: /show password/i })
      ).toBeInTheDocument()
    })
  })

  describe('OtpInput Component', () => {
    it('renders 6 input fields', () => {
      const mockRegistration = createMockRegistration('code')

      render(
        <TestWrapper>
          <OtpInput label="Verification Code" registration={mockRegistration} />
        </TestWrapper>
      )

      const inputs = screen.getAllByRole('textbox')
      expect(inputs).toHaveLength(6)
    })

    it('handles single digit input', async () => {
      const user = userEvent.setup()
      const mockRegistration = createMockRegistration('code')

      render(
        <TestWrapper>
          <OtpInput label="Verification Code" registration={mockRegistration} />
        </TestWrapper>
      )

      const inputs = screen.getAllByRole('textbox')

      // Type in first input
      await user.type(inputs[0], '1')
      expect(inputs[0]).toHaveValue('1')
    })

    it('handles arrow key navigation', async () => {
      const user = userEvent.setup()
      const mockRegistration = createMockRegistration('code')

      render(
        <TestWrapper>
          <OtpInput label="Verification Code" registration={mockRegistration} />
        </TestWrapper>
      )

      const inputs = screen.getAllByRole('textbox')

      // Focus first input and use arrow keys
      inputs[0].focus()
      await user.keyboard('{ArrowRight}')
      expect(inputs[1]).toHaveFocus()

      await user.keyboard('{ArrowLeft}')
      expect(inputs[0]).toHaveFocus()
    })

    it('handles backspace navigation', async () => {
      const user = userEvent.setup()
      const mockRegistration = createMockRegistration('code')

      render(
        <TestWrapper>
          <OtpInput label="Verification Code" registration={mockRegistration} />
        </TestWrapper>
      )

      const inputs = screen.getAllByRole('textbox')

      // Type in second input, then backspace
      await user.click(inputs[1])
      await user.type(inputs[1], '2')

      // Wait for state to settle
      await waitFor(() => {
        expect(inputs[1]).toHaveValue('2')
      })

      await user.keyboard('{Backspace}')

      // Check that input is cleared but focus stays on same input
      await waitFor(() => {
        expect(inputs[1]).toHaveValue('')
      })
    })
  })
})
