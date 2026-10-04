package com.example.hybrid;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {

    @GetMapping("/users")
    public List<String> listUsers() {
        return List.of();
    }

    @GetMapping("/users/{id}")
    public String getUser(@PathVariable String id) {
        return id;
    }

    @PostMapping("/users")
    public String createUser(@RequestBody String user) {
        return user;
    }
}
