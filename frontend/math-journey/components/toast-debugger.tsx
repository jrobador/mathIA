// FILE: frontend/math-journey/components/toast-debugger.tsx
"use client";

import React, { useEffect } from 'react';
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { CheckCircledIcon, CrossCircledIcon, InfoCircledIcon } from '@radix-ui/react-icons';

export function ToastDebugger() {
  // Test toast functionality when component mounts
  useEffect(() => {
    const initialToastId = toast.info("Toast debugger ready!", {
      duration: 2000,
      position: "bottom-right"
    });
    // Optional: Clear the initial toast after a bit
    // const timer = setTimeout(() => toast.dismiss(initialToastId), 2500);
    // return () => clearTimeout(timer);
  }, []);

  // Function to test different toast types
  const testToasts = () => {
    console.log("Testing toasts...");
    toast.success("Success toast test", {
        duration: 3000,
        position: "top-center",
        icon: <CheckCircledIcon className="text-green-500" />
    });

    setTimeout(() => {
      toast.error("Error toast test", {
        duration: 3000,
        position: "top-center",
        icon: <CrossCircledIcon className="text-red-500" />
      });
    }, 500); // Stagger slightly

    setTimeout(() => {
      toast.warning("Warning toast test", {
        duration: 3000,
        position: "top-center",
        icon: <InfoCircledIcon className="text-yellow-500" /> // Example icon
      });
    }, 1000);

    setTimeout(() => {
      toast.custom(
        (t) => (
          <div className="bg-indigo-100 border-l-4 border-indigo-500 p-4 rounded shadow-lg flex items-start">
            <InfoCircledIcon className="text-indigo-500 h-5 w-5 mt-0.5 mr-3 flex-shrink-0" />
            <div className="flex-grow">
                <p className="font-bold text-indigo-800">Custom Toast</p>
                <p className="text-sm text-indigo-700">This shows custom rendering works.</p>
            </div>
            <button onClick={() => toast.dismiss(t)} className="ml-4 text-gray-500 hover:text-gray-700 text-xs opacity-70 hover:opacity-100">X</button>
          </div>
        ),
        { duration: 4000, position: "top-center" }
      );
    }, 1500);
  };

  return (
    <div className="fixed bottom-4 right-4 z-[9999] bg-gray-800 text-white p-3 rounded-lg shadow-lg border border-gray-600 max-w-xs text-xs">
      <h3 className="text-sm font-semibold mb-2 border-b border-gray-600 pb-1">Toast Debugger</h3>
      <p className="mb-2 text-gray-300">Verify toast component functionality.</p>
      <Button onClick={testToasts} size="sm" variant="secondary" className="w-full">
        Test Toasts Now
      </Button>
    </div>
  );
}